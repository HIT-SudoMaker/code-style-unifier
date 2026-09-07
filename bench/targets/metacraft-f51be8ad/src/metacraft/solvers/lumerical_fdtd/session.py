from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import Decimal
import importlib.util
import math
import os
from pathlib import Path
import threading
from types import MappingProxyType
from typing import Any, Protocol

import numpy

from .qualification import LumericalUnavailable

_ENGINE_ENVIRONMENT_LOCK = threading.Lock()
_HALF_NANOMETRE_ROUND_TRIP_ABSOLUTE_TOLERANCE_NM = 1e-9
_GRATING_SETUP_BEGIN = "# METACRAFT_BEGIN_SPECIFIED_POSITION_T"
_GRATING_SETUP_END = "# METACRAFT_END_SPECIFIED_POSITION_T"
_GRATING_SETUP_CONTRACT = "\n".join(
    (
        _GRATING_SETUP_BEGIN,
        'select("T");',
        'set("spatial interpolation", "specified position");',
        _GRATING_SETUP_END,
    )
)


@dataclass(frozen=True, slots=True)
class _GratingResponsePlanes:
    """
    Carry the three physical grating-response planes across session IPC.
    """

    reflection_plane_z_nm: int
    source_plane_z_nm: int
    transmission_plane_z_nm: int

    def __post_init__(self) -> None:
        """
        Require exact integer nanometre positions at the session boundary.
        """

        if any(
            type(value) is not int
            for value in (
                self.reflection_plane_z_nm,
                self.source_plane_z_nm,
                self.transmission_plane_z_nm,
            )
        ):
            raise TypeError("grating_response_planes_invalid")

    def as_ipc_mapping(self) -> dict[str, int]:
        """
        Encode the complete process-safe plane value without coercion.
        """

        return {
            "reflection_plane_z_nm": self.reflection_plane_z_nm,
            "source_plane_z_nm": self.source_plane_z_nm,
            "transmission_plane_z_nm": self.transmission_plane_z_nm,
        }

    @classmethod
    def from_ipc_mapping(cls, value: object) -> _GratingResponsePlanes:
        """
        Decode only the exact three-field integer plane contract.
        """

        required_keys = {
            "reflection_plane_z_nm",
            "source_plane_z_nm",
            "transmission_plane_z_nm",
        }
        if not isinstance(value, Mapping) or set(value) != required_keys:
            raise RuntimeError("grating_response_planes_ipc_invalid")
        if any(type(value[key]) is not int for key in required_keys):
            raise RuntimeError("grating_response_planes_ipc_invalid")
        return cls(
            reflection_plane_z_nm=value["reflection_plane_z_nm"],
            source_plane_z_nm=value["source_plane_z_nm"],
            transmission_plane_z_nm=value["transmission_plane_z_nm"],
        )


@dataclass(frozen=True, slots=True)
class _OptionalResult:
    """
    Carries one returned result or exact product-reported absence over IPC.
    """

    response: Mapping[str, Any] | None

    def __post_init__(self) -> None:
        """
        Freeze a returned mapping while retaining exact absence as none.
        """

        if self.response is not None and not isinstance(
            self.response,
            Mapping,
        ):
            raise TypeError("optional_result_response_invalid")
        if self.response is not None:
            object.__setattr__(
                self,
                "response",
                MappingProxyType(dict(self.response)),
            )

    @classmethod
    def returned(cls, response: Mapping[str, Any]) -> _OptionalResult:
        """
        Retain one response the product explicitly returned.
        """

        return cls(response=response)

    @classmethod
    def response_not_returned(cls) -> _OptionalResult:
        """
        Retain exact absence reported by the product result inventory.
        """

        return cls(response=None)

    def as_ipc_mapping(self) -> dict[str, object]:
        """
        Encode one strict process-safe result envelope.
        """

        if self.response is None:
            return {"status": "response_not_returned"}
        return {
            "response": dict(self.response),
            "status": "returned",
        }

    @classmethod
    def from_ipc_mapping(cls, value: object) -> _OptionalResult:
        """
        Decode one strict process-safe result envelope.
        """

        if not isinstance(value, Mapping):
            raise RuntimeError("optional_result_ipc_invalid")
        if dict(value) == {"status": "response_not_returned"}:
            return cls.response_not_returned()
        if set(value) != {"response", "status"}:
            raise RuntimeError("optional_result_ipc_invalid")
        if value["status"] != "returned":
            raise RuntimeError("optional_result_ipc_invalid")
        response = value["response"]
        if not isinstance(response, Mapping):
            raise RuntimeError("optional_result_ipc_invalid")
        return cls.returned(response)


class Session(Protocol):
    """
    Defines the narrow template-facing solver session.
    """

    def create(
        self,
        kind: str,
        name: str,
        properties: Mapping[str, Any],
    ) -> None:
        """
        Create one named native object from declared properties.
        """

        ...

    def read(
        self,
        name: str,
        properties: tuple[str, ...],
    ) -> Mapping[str, Any]:
        """
        Read back the declared properties of one object.
        """

        ...

    def save(self, path: Path) -> None:
        """
        Save the exact current solver project.
        """

        ...

    def result(self, name: str, result_name: str) -> Mapping[str, Any]:
        """
        Read one named result from one named object.
        """

        ...

    def optional_result(
        self,
        name: str,
        result_name: str,
    ) -> _OptionalResult:
        """
        Read one result only when its complete native inventory exists.
        """

        ...

    def prepare_grating_response(self, name: str) -> _GratingResponsePlanes:
        """
        Pin and read the group-owned planes in world coordinates.
        """

        ...

    def change_maximum_time(
        self,
        name: str,
        maximum_time_fs: int,
    ) -> None:
        """
        Extend one constructed solver to its declared second time tier.
        """

        ...

    def reset(self) -> None:
        """
        Return the retained session to one empty construction state.
        """

        ...

    def close(self) -> None:
        """
        Release the solver session.
        """

        ...


# ---------------------------------------------------------------------------
# Product dialect
#
# The bidirectional dialect is the only place where a natural MetaCraft
# property name meets a native Lumerical spelling. Each entry binds the native
# name to its forward (public -> native) and inverse (native -> public) unit
# conversion. There is no underscore-to-space fallback: every kind and
# property emitted by the current periodic templates is named explicitly, and
# anything else fails before the engine is touched.
#
# Every native property is named explicitly below. The dialect never infers a
# product spelling from a public name.
# ---------------------------------------------------------------------------


def _to_metres(value: Any) -> float:
    return float(value) * 1e-9


def _from_metres(value: Any) -> int:
    return int(round(float(value) * 1e9))


def _from_half_nanometres(value: Any) -> int | float:
    """
    Normalize only SI round-trip noise around an exact half-nanometre center.
    """

    nanometres = float(value) * 1e9
    nearest_half_nanometre = round(nanometres * 2) / 2
    if not math.isclose(
        nanometres,
        nearest_half_nanometre,
        rel_tol=0.0,
        abs_tol=_HALF_NANOMETRE_ROUND_TRIP_ABSOLUTE_TOLERANCE_NM,
    ):
        return nanometres
    if nearest_half_nanometre.is_integer():
        return int(nearest_half_nanometre)
    return nearest_half_nanometre


def _to_seconds(value: Any) -> float:
    return float(value) * 1e-15


def _from_seconds(value: Any) -> int:
    return int(round(float(value) * 1e15))


def _to_native_float(value: Any) -> float:
    return float(value)


def _from_native_decimal(value: Any) -> Decimal:
    return Decimal(str(float(value)))


def _to_radius_metres(value: Any) -> float:
    return float(value) * 0.5e-9


def _from_radius_metres(value: Any) -> int:
    return int(round(float(value) * 2e9))


def _to_native_int(value: Any) -> int:
    return int(value)


def _from_native_number(value: Any) -> int:
    return int(round(float(value)))


def _identity(value: Any) -> Any:
    return value


def _to_native_bool(value: Any) -> int:
    return int(bool(value))


def _decode_native_bool(value: Any) -> bool:
    return bool(value)


def _to_periodic_boundary(value: Any) -> Any:
    return "Periodic" if value == "periodic" else value


def _from_periodic_boundary(value: Any) -> str:
    return str(value).lower()


def _to_absorbing_boundary(value: Any) -> Any:
    return "PML" if value == "absorbing" else value


def _from_absorbing_boundary(value: Any) -> str:
    return "absorbing" if value == "PML" else str(value).lower()


def _to_propagation_direction(value: Any) -> Any:
    if value == "positive":
        return 1
    if value == "negative":
        return 2
    return value


def _from_propagation_direction(value: Any) -> str:
    return "positive" if int(value) == 1 else "negative"


def _to_source_shape(value: Any) -> Any:
    return 1 if value == "plane wave" else value


def _from_source_shape(value: Any) -> str:
    return "plane wave" if int(value) == 1 else str(value)


_NativeEntry = tuple[str, Callable[[Any], Any], Callable[[Any], Any]]

# Length, time, integer, text, and boolean bindings are shared across the
# structural and solver objects that expose the same public name with the same
# native spelling. Shape-specific dimensions stay per kind below.
_SPAN_X: _NativeEntry = ("x span", _to_metres, _from_metres)
_SPAN_Y: _NativeEntry = ("y span", _to_metres, _from_metres)
_SPAN_Z: _NativeEntry = ("z span", _to_metres, _from_metres)
_LOWER_Z: _NativeEntry = ("z min", _to_metres, _from_metres)
_UPPER_Z: _NativeEntry = ("z max", _to_metres, _from_metres)
_POSITION_X: _NativeEntry = ("x", _to_metres, _from_metres)
_POSITION_Y: _NativeEntry = ("y", _to_metres, _from_metres)
_MATERIAL: _NativeEntry = ("material", _identity, _identity)

_FDTD_PROPERTIES: Mapping[str, _NativeEntry] = {
    "span_x_nm": _SPAN_X,
    "span_y_nm": _SPAN_Y,
    "lower_z_nm": _LOWER_Z,
    "upper_z_nm": _UPPER_Z,
    "lower_x_boundary": (
        "x min bc",
        _to_periodic_boundary,
        _from_periodic_boundary,
    ),
    "upper_x_boundary": (
        "x max bc",
        _to_periodic_boundary,
        _from_periodic_boundary,
    ),
    "lower_y_boundary": (
        "y min bc",
        _to_periodic_boundary,
        _from_periodic_boundary,
    ),
    "upper_y_boundary": (
        "y max bc",
        _to_periodic_boundary,
        _from_periodic_boundary,
    ),
    "lower_z_boundary": (
        "z min bc",
        _to_absorbing_boundary,
        _from_absorbing_boundary,
    ),
    "upper_z_boundary": (
        "z max bc",
        _to_absorbing_boundary,
        _from_absorbing_boundary,
    ),
    "mesh_accuracy": ("mesh accuracy", _to_native_int, _from_native_number),
    "simulation_time_fs": (
        "simulation time",
        _to_seconds,
        _from_seconds,
    ),
    "autoshutoff_threshold": (
        "auto shutoff min",
        _to_native_float,
        _from_native_decimal,
    ),
}

_RECTANGLE_PROPERTIES: Mapping[str, _NativeEntry] = {
    "material": _MATERIAL,
    "span_x_nm": _SPAN_X,
    "span_y_nm": _SPAN_Y,
    "lower_z_nm": _LOWER_Z,
    "upper_z_nm": _UPPER_Z,
    "position_x_nm": _POSITION_X,
    "position_y_nm": _POSITION_Y,
}

_CIRCLE_PROPERTIES: Mapping[str, _NativeEntry] = {
    "diameter_nm": ("radius", _to_radius_metres, _from_radius_metres),
    "material": _MATERIAL,
    "position_x_nm": _POSITION_X,
    "position_y_nm": _POSITION_Y,
    "lower_z_nm": _LOWER_Z,
    "upper_z_nm": _UPPER_Z,
}

_ELLIPSE_PROPERTIES: Mapping[str, _NativeEntry] = {
    "major_axis_nm": ("radius", _to_radius_metres, _from_radius_metres),
    "minor_axis_nm": ("radius 2", _to_radius_metres, _from_radius_metres),
    "material": _MATERIAL,
    "position_x_nm": _POSITION_X,
    "position_y_nm": _POSITION_Y,
    "lower_z_nm": _LOWER_Z,
    "upper_z_nm": _UPPER_Z,
}

_GRATING_RESPONSE_PROPERTIES: Mapping[str, _NativeEntry] = {
    "azimuth_degrees": ("angle phi", _to_native_int, _from_native_number),
    "polar_angle_degrees": (
        "angle theta",
        _to_native_int,
        _from_native_number,
    ),
    "meta_atom_center_nm": (
        "metamaterial center",
        _to_metres,
        _from_half_nanometres,
    ),
    "meta_atom_span_nm": (
        "metamaterial span",
        _to_metres,
        _from_metres,
    ),
    "polarization_angle_degrees": (
        "polarization angle",
        _to_native_int,
        _from_native_number,
    ),
    "propagation_axis": ("propagation axis", _identity, _identity),
    "propagation_direction": (
        "propagation direction",
        _to_propagation_direction,
        _from_propagation_direction,
    ),
    "source_offset_nm": ("source offset", _to_metres, _from_metres),
    "source_shape": ("source_type", _to_source_shape, _from_source_shape),
    "start_wavelength_nm": (
        "start wavelength",
        _to_metres,
        _from_metres,
    ),
    "stop_wavelength_nm": ("stop wavelength", _to_metres, _from_metres),
    "warnings_suppressed": (
        "suppress_warnings",
        _to_native_bool,
        _decode_native_bool,
    ),
    "target_transmission_order": (
        "target_grating_order_out",
        _to_native_int,
        _from_native_number,
    ),
    "relative_coordinates": (
        "use relative coordinates",
        _to_native_bool,
        _decode_native_bool,
    ),
    "span_x_nm": _SPAN_X,
    "span_y_nm": _SPAN_Y,
    "position_z_nm": ("z", _to_metres, _from_metres),
    "span_z_nm": _SPAN_Z,
}

_NATIVE_DIALECT: Mapping[str, Mapping[str, _NativeEntry]] = MappingProxyType(
    {
        "fdtd": MappingProxyType(_FDTD_PROPERTIES),
        "rectangle": MappingProxyType(_RECTANGLE_PROPERTIES),
        "circle": MappingProxyType(_CIRCLE_PROPERTIES),
        "ellipse": MappingProxyType(_ELLIPSE_PROPERTIES),
        "grating_response": MappingProxyType(_GRATING_RESPONSE_PROPERTIES),
    }
)


class LumericalSession:
    """
    The sole product boundary around a live ``lumapi.FDTD`` engine.
    """

    def __init__(self, engine: Any) -> None:
        """
        Retain one opened native engine.
        """

        self._engine = engine
        self._names: dict[str, str] = {}
        self._kinds: dict[str, str] = {}
        self._is_closed = False

    def create(
        self,
        kind: str,
        name: str,
        properties: Mapping[str, Any],
    ) -> None:
        """
        Map one product-neutral object into native Lumerical commands.

        Every kind and property is resolved through the bidirectional product
        dialect before the engine is touched, so an unknown kind or property
        fails here instead of inside the native call.
        """

        dialect = _NATIVE_DIALECT.get(kind)
        if dialect is None:
            raise ValueError(f"native_object_unsupported:{kind}")
        translated: list[tuple[str, Any]] = []
        for key, value in properties.items():
            entry = dialect.get(key)
            if entry is None:
                raise ValueError(
                    f"native_property_unsupported:{kind}:{key}"
                )
            native_key = entry[0]
            to_native = entry[1]
            translated.append((native_key, to_native(value)))
        if kind == "fdtd":
            self._engine.addfdtd()
            native_name = "FDTD"
        elif kind == "rectangle":
            self._engine.addrect()
            native_name = name
        elif kind in {"circle", "ellipse"}:
            self._engine.addcircle()
            native_name = name
        else:
            assert kind == "grating_response"
            self._engine.addobject("grating_s_params")
            native_name = name
        if native_name == name:
            self._engine.set("name", name)
        self._names[name] = native_name
        self._kinds[name] = kind
        for native_key, native_value in translated:
            self._engine.set(native_key, native_value)

    def read(
        self,
        name: str,
        properties: tuple[str, ...],
    ) -> Mapping[str, Any]:
        """
        Read native properties back into contract units.

        The dialect resolves every requested property before any native read,
        so an unsupported inverse read fails here instead of inside the engine.
        """

        kind = self._kinds.get(name)
        if kind is None:
            raise ValueError(f"native_object_unknown:{name}")
        dialect = _NATIVE_DIALECT[kind]
        native_name = self._names[name]
        plan: list[tuple[str, str, Callable[[Any], Any]]] = []
        for property_name in properties:
            entry = dialect.get(property_name)
            if entry is None:
                raise ValueError(
                    f"native_read_unsupported:{kind}:{property_name}"
                )
            native_key = entry[0]
            to_public = entry[2]
            plan.append((property_name, native_key, to_public))
        observed: dict[str, Any] = {}
        for property_name, native_key, to_public in plan:
            value = self._engine.getnamed(native_name, native_key)
            observed[property_name] = to_public(value)
        return observed

    def save(self, path: Path) -> None:
        """
        Save the current native project at an explicit run path.
        """

        self._engine.save(str(path))

    def solve(self, before: Path, after: Path) -> None:
        """
        Execute one project inside this session's lane-owned process tree.
        """

        if self._is_closed:
            raise RuntimeError("lumerical_session_closed")
        self.save(before)
        for name, kind in self._kinds.items():
            if kind == "grating_response":
                self._validate_grating_response_interpolation(
                    self._names[name]
                )
        self._engine.run()
        self.save(after)

    def result(self, name: str, result_name: str) -> Mapping[str, Any]:
        """
        Translate native grating datasets into one stable observation.
        """

        native_name = self._names.get(name, name)
        if result_name == "termination":
            if self._kinds.get(name) != "fdtd":
                raise ValueError("solver_termination_owner_invalid")
            return _solver_termination(self._engine, native_name)
        if result_name == "propagation":
            self._engine.runanalysis(native_name)
            scattering = self._engine.getresult(native_name, "S")
            power = self._engine.getresult(native_name, "T")
            return {
                "complex_transmission": _complex_scalar(scattering["S21_Gn"]),
                "phase_planes": "metamaterial_surfaces",
                "power_transmission": float(
                    numpy.real(_complex_scalar(power["T_Gn"])),
                ),
                "solver_status": "complete",
                "warnings": (),
            }
        if result_name == "reference_surface":
            self._engine.runanalysis(native_name)
            return _reference_surface_result(self._engine, native_name)
        if result_name == "linear_transmission":
            self._engine.runanalysis(native_name)
            scattering = self._engine.getresult(
                native_name,
                "S_polarization",
            )
            polarized = numpy.asarray(
                scattering["S21_Gn"]
            ).squeeze()
            if polarized.size != 2:
                raise ValueError("grating_polarization_shape_invalid")
            s_component, p_component = (
                complex(value) for value in polarized.reshape(-1)
            )
            return {
                "output_x": p_component,
                "output_y": s_component,
                "phase_planes": "metamaterial_surfaces",
                "solver_status": "complete",
                "warnings": (),
            }
        return self._engine.getresult(native_name, result_name)

    def change_maximum_time(
        self,
        name: str,
        maximum_time_fs: int,
    ) -> None:
        """
        Enter layout mode and apply one exact declared maximum-time change.
        """

        if self._kinds.get(name) != "fdtd":
            raise ValueError("solver_time_owner_invalid")
        if type(maximum_time_fs) is not int or maximum_time_fs <= 0:
            raise ValueError("solver_maximum_time_invalid")
        native_name = self._names[name]
        self._engine.switchtolayout()
        self._engine.setnamed(
            native_name,
            "simulation time",
            _to_seconds(maximum_time_fs),
        )
        observed = _from_seconds(
            self._engine.getnamed(native_name, "simulation time")
        )
        if observed != maximum_time_fs:
            raise RuntimeError("solver_maximum_time_read_back_mismatch")

    def optional_result(
        self,
        name: str,
        result_name: str,
    ) -> _OptionalResult:
        """
        Return explicit absence only from the native result inventory.
        """

        native_name = self._names.get(name, name)
        if result_name == "propagation":
            required_results = (
                (native_name, "S"),
                (native_name, "T"),
            )
        elif result_name == "linear_transmission":
            required_results = ((native_name, "S_polarization"),)
        elif result_name == "reference_surface":
            monitor_name = f"{native_name}::T"
            required_results = (
                (monitor_name, "E"),
                (monitor_name, "T"),
            )
        else:
            raise ValueError(
                f"optional_native_result_unsupported:{result_name}"
            )
        self._engine.runanalysis(native_name)
        result_availability = tuple(
            bool(self._engine.haveresult(result_owner, native_result))
            for result_owner, native_result in required_results
        )
        if all(result_availability):
            return _OptionalResult.returned(
                self.result(name, result_name)
            )
        return _OptionalResult.response_not_returned()

    def prepare_grating_response(self, name: str) -> _GratingResponsePlanes:
        """
        Pin the T monitor before reading every internal plane in world space.
        """

        native_name = self._names.get(name, name)
        self._ensure_grating_setup_contract(native_name)
        self._engine.runsetup()
        self._validate_grating_response_interpolation(native_name)
        center = float(self._engine.getnamed(native_name, "z"))
        is_relative = bool(
            self._engine.getnamed(
                native_name,
                "use relative coordinates",
            )
        )

        def _world_z_nm(child: str) -> int:
            position = float(
                self._engine.getnamed(f"{native_name}::{child}", "z")
            )
            if is_relative:
                position += center
            return int(round(position * 1e9))

        return _GratingResponsePlanes(
            reflection_plane_z_nm=_world_z_nm("R"),
            source_plane_z_nm=_world_z_nm("source"),
            transmission_plane_z_nm=_world_z_nm("T"),
        )

    def _ensure_grating_setup_contract(self, native_name: str) -> None:
        setup_script = self._engine.getnamed(native_name, "setup script")
        if not isinstance(setup_script, str):
            raise RuntimeError("grating_setup_script_invalid")
        begin_count = setup_script.count(_GRATING_SETUP_BEGIN)
        end_count = setup_script.count(_GRATING_SETUP_END)
        if begin_count > 1 or end_count > 1:
            raise RuntimeError("grating_setup_contract_duplicate")
        if begin_count != end_count:
            raise RuntimeError("grating_setup_contract_incomplete")
        if begin_count == 1:
            begin = setup_script.index(_GRATING_SETUP_BEGIN)
            end = setup_script.find(
                _GRATING_SETUP_END,
                begin + len(_GRATING_SETUP_BEGIN),
            )
            if end < 0:
                raise RuntimeError("grating_setup_contract_conflict")
            end += len(_GRATING_SETUP_END)
            if setup_script[begin:end] != _GRATING_SETUP_CONTRACT:
                raise RuntimeError("grating_setup_contract_conflict")
            return
        separator = (
            ""
            if not setup_script or setup_script.endswith(("\n", "\r"))
            else "\n"
        )
        self._engine.setnamed(
            native_name,
            "setup script",
            f"{setup_script}{separator}{_GRATING_SETUP_CONTRACT}",
        )

    def _validate_grating_response_interpolation(
        self,
        native_name: str,
    ) -> None:
        transmission_name = f"{native_name}::T"
        if (
            self._engine.getnamed(
                transmission_name,
                "spatial interpolation",
            )
            != "specified position"
        ):
            raise RuntimeError(
                "grating_transmission_interpolation_mismatch"
            )

    def close(self) -> None:
        """
        Close the native engine.
        """

        if not self._is_closed:
            self._engine.close()
            self._is_closed = True

    def reset(self) -> None:
        """
        Clear the completed construction before the next candidate.
        """

        if self._is_closed:
            raise RuntimeError("lumerical_session_closed")
        self._engine.switchtolayout()
        self._engine.deleteall()
        self._names.clear()
        self._kinds.clear()


def open_engine(
    python_api: Path,
    *,
    should_hide: bool = True,
    license_server: str | None = None,
) -> Any:
    """
    Load the exact configured API and open one native FDTD engine.
    """

    spec = importlib.util.spec_from_file_location("lumapi", python_api)
    if spec is None or spec.loader is None:
        raise RuntimeError("lumapi_load_failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with _ENGINE_ENVIRONMENT_LOCK:
        previous = os.environ.get("ANSYSLMD_LICENSE_FILE")
        if license_server:
            os.environ["ANSYSLMD_LICENSE_FILE"] = license_server
        try:
            return module.FDTD(hide=should_hide)
        except Exception as error:
            product_error = getattr(module, "LumApiError", None)
            if (
                isinstance(product_error, type)
                and issubclass(product_error, BaseException)
                and isinstance(error, product_error)
            ):
                raise LumericalUnavailable(
                    "native_product_unavailable"
                ) from error
            raise
        finally:
            if previous is None:
                os.environ.pop("ANSYSLMD_LICENSE_FILE", None)
            else:
                os.environ["ANSYSLMD_LICENSE_FILE"] = previous


def open_session(
    python_api: Path,
    *,
    should_hide: bool = True,
    license_server: str | None = None,
) -> LumericalSession:
    """
    Wrap one exact native FDTD engine behind the session contract.
    """

    return LumericalSession(
        open_engine(
            python_api,
            should_hide=should_hide,
            license_server=license_server,
        )
    )


def _complex_scalar(value: Any) -> complex:
    """
    Extract one complex scalar from a single-wavelength native dataset.
    """

    values = numpy.asarray(value).squeeze()
    if values.size != 1:
        raise ValueError("grating_single_wavelength_required")
    return complex(values.reshape(-1)[0])


def _reference_surface_result(
    engine: Any,
    native_name: str,
) -> dict[str, object]:
    """
    Read the grating group's own transmitted near-field reference plane.

    ``grating_s_params`` owns an internal ``T`` monitor. Reading that monitor
    exposes the sampled field used by grating projection without adding a
    second source or monitor to the periodic template.
    """

    monitor_name = f"{native_name}::T"
    dataset = engine.getresult(monitor_name, "E")
    transmitted = engine.getresult(monitor_name, "T")
    electric = numpy.asarray(dataset["E"])
    x_coordinates = numpy.asarray(dataset["x"]).reshape(-1)
    y_coordinates = numpy.asarray(dataset["y"]).reshape(-1)
    z_coordinates = numpy.asarray(dataset["z"]).reshape(-1)
    if (
        electric.ndim != 5
        or electric.shape[-1] != 3
        or electric.shape[2:4] != (1, 1)
        or x_coordinates.size < 3
        or y_coordinates.size < 3
        or z_coordinates.size != 1
        or electric.shape[:2]
        != (x_coordinates.size, y_coordinates.size)
        or not numpy.isfinite(x_coordinates).all()
        or not numpy.isfinite(y_coordinates).all()
        or not numpy.isfinite(z_coordinates).all()
        or not numpy.isfinite(electric.real).all()
        or not numpy.isfinite(electric.imag).all()
    ):
        raise ValueError("reference_surface_native_shape_invalid")
    x_differences = numpy.diff(
        x_coordinates.astype(numpy.float64, copy=False)
    )
    y_differences = numpy.diff(
        y_coordinates.astype(numpy.float64, copy=False)
    )
    if not (numpy.all(x_differences > 0) and numpy.all(y_differences > 0)):
        raise ValueError("reference_surface_native_coordinates_invalid")
    x_period = float(x_coordinates[-1] - x_coordinates[0])
    y_period = float(y_coordinates[-1] - y_coordinates[0])
    if (
        not math.isclose(
            x_period,
            y_period,
            rel_tol=1e-9,
            abs_tol=1e-15,
        )
        or not numpy.allclose(
            electric[0, ...],
            electric[-1, ...],
            rtol=1e-9,
            atol=1e-15,
        )
        or not numpy.allclose(
            electric[:, 0, ...],
            electric[:, -1, ...],
            rtol=1e-9,
            atol=1e-15,
        )
    ):
        raise ValueError("reference_surface_native_closed_grid_invalid")
    electric = electric[:, :, 0, 0, :].transpose(1, 0, 2)
    angle_value = float(
        engine.getnamed(native_name, "polarization angle")
    )
    angle = int(round(angle_value))
    wavelength_m = float(engine.getnamed(native_name, "start wavelength"))
    transmitted_power = float(
        numpy.real(_complex_scalar(transmitted["T"]))
    )
    if (
        not math.isfinite(angle_value)
        or not math.isclose(angle_value, angle, rel_tol=0, abs_tol=1e-12)
        or angle not in {0, 90}
        or not math.isfinite(wavelength_m)
        or wavelength_m <= 0
        or not math.isfinite(transmitted_power)
        or transmitted_power < 0
    ):
        raise ValueError("reference_surface_native_context_invalid")
    components = {
        name: {
            "imaginary": numpy.imag(electric[..., index]).tolist(),
            "real": numpy.real(electric[..., index]).tolist(),
        }
        for index, name in enumerate(("x", "y", "z"))
    }
    return {
        "electric_components": components,
        "frame": {
            "normal_axis": "z",
            "propagation_direction": "positive",
            "sample_order": ["y", "x"],
        },
        "incident_reference_power": "1",
        "medium": "transmission medium",
        "order_regime": "multi order",
        "output_basis": "cartesian",
        "requested_input_basis": (
            "x linear" if angle == 0 else "y linear"
        ),
        "surface": {
            "position_m": format(float(z_coordinates[0]), ".17g"),
            "x_coordinates_m": [
                format(float(value), ".17g") for value in x_coordinates
            ],
            "y_coordinates_m": [
                format(float(value), ".17g") for value in y_coordinates
            ],
        },
        "transmitted_power": format(
            transmitted_power,
            ".17g",
        ),
        "wavelength_m": format(wavelength_m, ".17g"),
    }


def _solver_termination(engine: Any, native_name: str) -> dict[str, object]:
    """
    Translate native status and the terminal energy sample into stable units.
    """

    native_status = int(round(float(engine.getresult(native_name, "status"))))
    outcomes = {
        1: "maximum_time",
        2: "autoshutoff",
        3: "diverged",
    }
    outcome = outcomes.get(native_status)
    if outcome is None:
        raise RuntimeError("solver_termination_status_unknown")
    history = engine.getresult(native_name, "autoshutoff level")
    if not isinstance(history, Mapping):
        raise RuntimeError("solver_autoshutoff_history_invalid")
    times = numpy.asarray(history.get("t"), dtype=numpy.float64).reshape(-1)
    levels = numpy.asarray(
        history.get("autoshutoff"),
        dtype=numpy.float64,
    ).reshape(-1)
    if (
        times.size == 0
        or times.size != levels.size
        or not numpy.isfinite(times).all()
        or not numpy.isfinite(levels).all()
        or times[-1] <= 0
        or levels[-1] < 0
    ):
        raise RuntimeError("solver_autoshutoff_history_invalid")
    threshold = float(engine.getnamed(native_name, "auto shutoff min"))
    if not math.isfinite(threshold) or not 0 < threshold < 1:
        raise RuntimeError("solver_autoshutoff_threshold_invalid")
    return {
        "autoshutoff_threshold": threshold,
        "native_status": native_status,
        "outcome": outcome,
        "simulated_time_fs": float(times[-1] * 1e15),
        "terminal_autoshutoff": float(levels[-1]),
    }
