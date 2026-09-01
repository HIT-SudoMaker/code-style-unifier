from __future__ import annotations

import base64
import csv
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
import hashlib
import io

import yaml

from ..authority import Document, Reference
from ..canonical import encode_bytes
from .source import MaterialSource


@dataclass(frozen=True, slots=True)
class OpticalPoint:
    """
    Holds one wavelength-index-loss observation.
    """

    wavelength_nm: Decimal
    refractive_index: Decimal
    extinction_coefficient: Decimal

    def encode_mapping(self) -> dict[str, str]:
        """
        Return this optical point without binary floating-point loss.
        """

        return {
            "extinction_coefficient": format(
                self.extinction_coefficient,
                "f",
            ),
            "refractive_index": format(self.refractive_index, "f"),
            "wavelength_nm": format(self.wavelength_nm, "f"),
        }


@dataclass(frozen=True, slots=True)
class MaterialColumns:
    """
    Retains how source columns were interpreted.
    """

    wavelength: str
    refractive_index: str
    extinction_coefficient: str

    def encode_mapping(self) -> dict[str, str]:
        """
        Return the declared source-column meanings.
        """

        return {
            "extinction_coefficient": self.extinction_coefficient,
            "refractive_index": self.refractive_index,
            "wavelength": self.wavelength,
        }


@dataclass(frozen=True, slots=True)
class MaterialSample:
    """
    Records one resolved optical sample and interpolation policy.
    """

    wavelength_nm: Decimal
    refractive_index: Decimal
    extinction_coefficient: Decimal
    interpolation: str
    record_identity: str
    record_reference: Reference | None = None

    def with_record(self, reference: Reference) -> MaterialSample:
        """
        Bind this optical sample to its admitted material record.
        """

        return replace(self, record_reference=reference)

    def encode_document(self) -> Document:
        """
        Encode this resolved sample for exact authority storage.
        """

        if self.record_reference is None:
            raise ValueError("material_record_reference_missing")
        return Document(
            "metacraft.material.sample",
            {
                "extinction_coefficient": format(
                    self.extinction_coefficient,
                    "f",
                ),
                "interpolation": self.interpolation,
                "record_identity": self.record_identity,
                "record_reference": self.record_reference.as_mapping(),
                "refractive_index": format(self.refractive_index, "f"),
                "wavelength_nm": format(self.wavelength_nm, "f"),
            },
        )

    @classmethod
    def decode_document_bytes(cls, value: bytes) -> MaterialSample:
        """
        Decode one canonical material sample.
        """

        document = Document.from_bytes(value)
        if document.schema_identifier != "metacraft.material.sample":
            raise ValueError("material_sample_schema_invalid")
        values = document.values
        return cls(
            wavelength_nm=Decimal(values["wavelength_nm"]),
            refractive_index=Decimal(values["refractive_index"]),
            extinction_coefficient=Decimal(values["extinction_coefficient"]),
            interpolation=str(values["interpolation"]),
            record_identity=str(values["record_identity"]),
            record_reference=Reference.from_mapping(values["record_reference"]),
        )


@dataclass(frozen=True, slots=True)
class MaterialRecord:
    """
    Retains portable optical data with immutable source bytes.
    """

    source_kind: MaterialSource
    source_name: str
    source_identity: str
    record_identity: str
    source_bytes: bytes
    attribution: str
    declared_wavelength_unit: str
    columns: MaterialColumns
    points: tuple[OpticalPoint, ...]

    def __post_init__(self) -> None:
        """
        Keep portable records on MetaCraft-owned material sources.
        """

        if (
            not isinstance(self.source_kind, MaterialSource)
            or self.source_kind
            not in {
                MaterialSource.LOCAL_TABLE,
                MaterialSource.REFRACTIVEINDEX_INFO_DATASET,
            }
        ):
            raise ValueError("material_record_source_invalid")

    @property
    def covered_band_nm(self) -> tuple[Decimal, Decimal]:
        """
        Return the closed wavelength interval covered by this record.
        """

        return self.points[0].wavelength_nm, self.points[-1].wavelength_nm

    def sample(
        self,
        wavelength_nm: Decimal,
        *,
        interpolation: str = "linear",
    ) -> MaterialSample:
        """
        Resolve one in-band wavelength without silent extrapolation.
        """

        if interpolation != "linear":
            raise ValueError("interpolation_unsupported")
        lower_band, upper_band = self.covered_band_nm
        if not lower_band <= wavelength_nm <= upper_band:
            raise ValueError("outside_covered_band")
        for point in self.points:
            if point.wavelength_nm == wavelength_nm:
                return MaterialSample(
                    wavelength_nm=wavelength_nm,
                    refractive_index=point.refractive_index,
                    extinction_coefficient=point.extinction_coefficient,
                    interpolation=interpolation,
                    record_identity=self.record_identity,
                )
        for lower, upper in zip(self.points, self.points[1:], strict=False):
            if lower.wavelength_nm < wavelength_nm < upper.wavelength_nm:
                fraction = (wavelength_nm - lower.wavelength_nm) / (
                    upper.wavelength_nm - lower.wavelength_nm
                )
                return MaterialSample(
                    wavelength_nm=wavelength_nm,
                    refractive_index=(
                        lower.refractive_index
                        + fraction * (upper.refractive_index - lower.refractive_index)
                    ),
                    extinction_coefficient=(
                        lower.extinction_coefficient
                        + fraction
                        * (upper.extinction_coefficient - lower.extinction_coefficient)
                    ),
                    interpolation=interpolation,
                    record_identity=self.record_identity,
                )
        raise AssertionError("covered wavelength lacked interpolation bracket")

    def encode_document(self) -> Document:
        """
        Encode this record for exact authority storage.
        """

        return Document(
            "metacraft.material.record",
            {
                "attribution": self.attribution,
                "columns": self.columns.encode_mapping(),
                "declared_wavelength_unit": self.declared_wavelength_unit,
                "points": [point.encode_mapping() for point in self.points],
                "record_identity": self.record_identity,
                "source_bytes_base64": base64.b64encode(self.source_bytes).decode(
                    "ascii"
                ),
                "source_identity": self.source_identity,
                "source_kind": self.source_kind,
                "source_name": self.source_name,
            },
        )

    @classmethod
    def decode_document_bytes(cls, value: bytes) -> MaterialRecord:
        """
        Decode a record and verify its retained source identity.
        """

        document = Document.from_bytes(value)
        if document.schema_identifier != "metacraft.material.record":
            raise ValueError("material_document_schema_invalid")
        values = document.values
        points = tuple(
            OpticalPoint(
                wavelength_nm=Decimal(point["wavelength_nm"]),
                refractive_index=Decimal(point["refractive_index"]),
                extinction_coefficient=Decimal(point["extinction_coefficient"]),
            )
            for point in values["points"]
        )
        record = cls(
            source_kind=MaterialSource(str(values["source_kind"])),
            source_name=str(values["source_name"]),
            source_identity=str(values["source_identity"]),
            record_identity=str(values["record_identity"]),
            source_bytes=base64.b64decode(values["source_bytes_base64"]),
            attribution=str(values["attribution"]),
            declared_wavelength_unit=str(values["declared_wavelength_unit"]),
            columns=MaterialColumns(
                wavelength=str(values["columns"]["wavelength"]),
                refractive_index=str(values["columns"]["refractive_index"]),
                extinction_coefficient=str(values["columns"]["extinction_coefficient"]),
            ),
            points=points,
        )
        if _identity(record.source_bytes) != record.source_identity:
            raise ValueError("material_source_identity_mismatch")
        if (
            _record_identity(
                source_kind=record.source_kind,
                source_name=record.source_name,
                source_identity=record.source_identity,
                attribution=record.attribution,
                declared_wavelength_unit=record.declared_wavelength_unit,
                columns=record.columns,
                points=record.points,
            )
            != record.record_identity
        ):
            raise ValueError("material_record_identity_mismatch")
        return record


def parse_local_table(
    source_bytes: bytes,
    *,
    wavelength_unit: str,
    source_name: str,
    wavelength_column: str = "wavelength",
    refractive_index_column: str = "n",
    extinction_column: str = "k",
) -> MaterialRecord:
    """
    Parse an explicit user table into one portable material record.
    """

    rows = _table_rows(source_bytes)
    required = {
        wavelength_column,
        refractive_index_column,
        extinction_column,
    }
    if not rows or not required.issubset(rows[0]):
        raise ValueError("material_columns_missing")
    factor = _unit_factor(wavelength_unit)
    points = []
    for row in rows:
        try:
            wavelength = Decimal(row[wavelength_column]) * factor
            refractive_index = Decimal(row[refractive_index_column])
            extinction = Decimal(row[extinction_column])
        except (InvalidOperation, KeyError):
            raise ValueError("material_value_invalid") from None
        points.append(OpticalPoint(wavelength, refractive_index, extinction))
    return _record(
        source_kind=MaterialSource.LOCAL_TABLE,
        source_name=source_name,
        source_bytes=source_bytes,
        attribution=f"user:{source_name}",
        declared_wavelength_unit=wavelength_unit,
        columns=MaterialColumns(
            wavelength=wavelength_column,
            refractive_index=refractive_index_column,
            extinction_coefficient=extinction_column,
        ),
        points=points,
    )


def parse_refractiveindex_info(
    source_bytes: bytes,
    *,
    source_url: str,
) -> MaterialRecord:
    """
    Parse downloaded tabulated nk source bytes without fetching them.
    """

    try:
        source = yaml.safe_load(source_bytes)
    except yaml.YAMLError as error:
        raise ValueError("refractiveindex_info_yaml_invalid") from error
    entries = source.get("DATA") if isinstance(source, dict) else None
    if not isinstance(entries, list):
        raise ValueError("refractiveindex_info_data_missing")
    tabulated = next(
        (
            entry
            for entry in entries
            if isinstance(entry, dict)
            and str(entry.get("type", "")).strip().lower() == "tabulated nk"
        ),
        None,
    )
    if tabulated is None or not isinstance(tabulated.get("data"), str):
        raise ValueError("refractiveindex_info_tabulated_nk_missing")
    points = []
    for line in tabulated["data"].splitlines():
        values = line.split()
        if not values:
            continue
        if len(values) != 3:
            raise ValueError("refractiveindex_info_row_invalid")
        try:
            wavelength_um, refractive_index, extinction = map(
                Decimal,
                values,
            )
        except InvalidOperation:
            raise ValueError("refractiveindex_info_value_invalid") from None
        points.append(
            OpticalPoint(
                wavelength_nm=wavelength_um * Decimal(1000),
                refractive_index=refractive_index,
                extinction_coefficient=extinction,
            )
        )
    return _record(
        source_kind=MaterialSource.REFRACTIVEINDEX_INFO_DATASET,
        source_name=source_url.rsplit("/", 1)[-1],
        source_bytes=source_bytes,
        attribution=source_url,
        declared_wavelength_unit="um",
        columns=MaterialColumns(
            wavelength="wavelength",
            refractive_index="n",
            extinction_coefficient="k",
        ),
        points=points,
    )


def _record(
    *,
    source_kind: MaterialSource,
    source_name: str,
    source_bytes: bytes,
    attribution: str,
    declared_wavelength_unit: str,
    columns: MaterialColumns,
    points: list[OpticalPoint],
) -> MaterialRecord:
    if len(points) < 2:
        raise ValueError("material_points_insufficient")
    ordered = tuple(sorted(points, key=lambda point: point.wavelength_nm))
    for point in ordered:
        if (
            not point.wavelength_nm.is_finite()
            or not point.refractive_index.is_finite()
            or not point.extinction_coefficient.is_finite()
            or point.wavelength_nm <= 0
            or point.refractive_index <= 0
            or point.extinction_coefficient < 0
        ):
            raise ValueError("material_value_invalid")
    wavelengths = [point.wavelength_nm for point in ordered]
    if len(set(wavelengths)) != len(wavelengths):
        raise ValueError("wavelength_duplicate")
    source_identity = _identity(source_bytes)
    record_identity = _record_identity(
        source_kind=source_kind,
        source_name=source_name,
        source_identity=source_identity,
        attribution=attribution,
        declared_wavelength_unit=declared_wavelength_unit,
        columns=columns,
        points=ordered,
    )
    return MaterialRecord(
        source_kind=source_kind,
        source_name=source_name,
        source_identity=source_identity,
        record_identity=record_identity,
        source_bytes=source_bytes,
        attribution=attribution,
        declared_wavelength_unit=declared_wavelength_unit,
        columns=columns,
        points=ordered,
    )


def _table_rows(source_bytes: bytes) -> list[dict[str, str]]:
    try:
        text = source_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("material_text_not_utf8") from error
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("material_table_empty")
    if "," in lines[0]:
        reader = csv.DictReader(io.StringIO("\n".join(lines)))
        if reader.fieldnames is None or len(set(reader.fieldnames)) != len(
            reader.fieldnames
        ):
            raise ValueError("material_columns_ambiguous")
        return [
            {str(key).strip(): str(value).strip() for key, value in row.items()}
            for row in reader
        ]
    headers = lines[0].split()
    if len(set(headers)) != len(headers):
        raise ValueError("material_columns_ambiguous")
    rows = []
    for line in lines[1:]:
        values = line.split()
        if len(values) != len(headers):
            raise ValueError("material_row_width_invalid")
        rows.append(dict(zip(headers, values, strict=True)))
    return rows


def _unit_factor(unit: str) -> Decimal:
    factors = {
        "m": Decimal("1e9"),
        "nm": Decimal(1),
        "um": Decimal(1000),
    }
    try:
        return factors[unit]
    except KeyError:
        raise ValueError("wavelength_unit_unsupported") from None


def _identity(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _record_identity(
    *,
    source_kind: MaterialSource,
    source_name: str,
    source_identity: str,
    attribution: str,
    declared_wavelength_unit: str,
    columns: MaterialColumns,
    points: tuple[OpticalPoint, ...],
) -> str:
    return _identity(
        encode_bytes(
            {
                "attribution": attribution,
                "columns": columns.encode_mapping(),
                "declared_wavelength_unit": declared_wavelength_unit,
                "points": [point.encode_mapping() for point in points],
                "source_identity": source_identity,
                "source_kind": source_kind,
                "source_name": source_name,
            }
        )
    )
