from __future__ import annotations

from collections.abc import Mapping
import json

from ..authority import Document, Reference
from ..authority.session import AuthoritySession
from ..canonical import canonicalize, encode_bytes
from ..external_activity import ExternalActivityClosure
from ..science.periodic_response import (
    PERIODIC_OBSERVATION_INCOMPLETE_SCHEMA,
    AdmittedPeriodicObservationIncomplete,
    AdmittedPeriodicPolarization,
    AdmittedPeriodicTransmission,
    ObservedPeriodicPolarization,
    ObservedPeriodicTransmission,
    PeriodicPolarizationObservation,
    PeriodicPolarizationIncomplete,
    PeriodicPolarizationRequest,
    PeriodicResponseOutcome,
    PeriodicResponseClosure,
    PeriodicResponseContext,
    PeriodicResponseRequest,
    PeriodicResponseUnavailable,
    PeriodicResponseUnavailableReason,
    PeriodicTransmissionObservation,
    PeriodicTransmissionIncomplete,
    PeriodicTransmissionRequest,
    PeriodicWork,
    form_admitted_periodic_polarization,
    form_admitted_periodic_transmission,
    decode_periodic_observation_incomplete,
    decode_periodic_polarization,
    decode_periodic_transmission,
)
from ..work_execution import PERMITTED_WORK_SCHEMA


class RecordedPeriodicResponse:
    """
    Restore exact consumed response receipts without opening a new work life.
    """

    __slots__ = ("_context", "_session")

    def __init__(
        self,
        session: AuthoritySession,
        *,
        context: PeriodicResponseContext,
    ) -> None:
        """
        Bind exact recorded receipts and their optional response context.
        """

        self._session = session
        self._context = PeriodicResponseContext(
            binding_reference=context.binding_reference,
            capacity_scope=context.capacity_scope,
            response_kinds=context.response_kinds,
            qualification_closure=ExternalActivityClosure.recorded(),
        )

    @property
    def context(self) -> PeriodicResponseContext:
        """
        Return the exact context explicitly recorded for a fresh run.
        """

        return self._context

    def observe(
        self,
        request: PeriodicResponseRequest,
    ) -> PeriodicResponseOutcome:
        """
        Restore one sealed request without current native activity.
        """

        if type(request) is PeriodicTransmissionRequest:
            restored = tuple(self._restore_transmission(item) for item in request.items)
            if any(item is None for item in restored):
                return PeriodicResponseUnavailable(
                    request.request_identity,
                    PeriodicResponseUnavailableReason.RECORDED_RESPONSE_MISSING,
                    self._closure(request.request_identity),
                )
            items = tuple(
                item
                for item in restored
                if isinstance(item, AdmittedPeriodicTransmission)
            )
            incomplete = tuple(
                item
                for item in restored
                if isinstance(item, AdmittedPeriodicObservationIncomplete)
            )
            if incomplete:
                return PeriodicTransmissionIncomplete(
                    request.request_identity,
                    items,
                    incomplete,
                    self._closure(request.request_identity),
                )
            return ObservedPeriodicTransmission(
                request.request_identity,
                items,
                self._closure(request.request_identity),
            )
        if type(request) is PeriodicPolarizationRequest:
            restored = tuple(self._restore_polarization(item) for item in request.items)
            if any(item is None for item in restored):
                return PeriodicResponseUnavailable(
                    request.request_identity,
                    PeriodicResponseUnavailableReason.RECORDED_RESPONSE_MISSING,
                    self._closure(request.request_identity),
                )
            items = tuple(
                item
                for item in restored
                if isinstance(item, AdmittedPeriodicPolarization)
            )
            incomplete = tuple(
                item
                for item in restored
                if isinstance(item, AdmittedPeriodicObservationIncomplete)
            )
            if incomplete:
                return PeriodicPolarizationIncomplete(
                    request.request_identity,
                    items,
                    incomplete,
                    self._closure(request.request_identity),
                )
            return ObservedPeriodicPolarization(
                request.request_identity,
                items,
                self._closure(request.request_identity),
            )
        raise TypeError("periodic_response_request_unsupported")

    def _closure(self, request_identity: str) -> PeriodicResponseClosure:
        return PeriodicResponseClosure(
            request_identity=request_identity,
            qualification=ExternalActivityClosure.recorded(),
            observation=ExternalActivityClosure.recorded(),
        )

    def _matching_documents(
        self,
        work: PeriodicWork,
    ) -> tuple[tuple[Document, Reference, Reference], ...]:
        matches: list[tuple[Document, Reference, Reference]] = []
        for permit in self._session.observe().permits:
            if permit.scope != work.capacity_scope:
                continue
            permit_document = self._document(
                permit.body_reference,
                "periodic_work_document_invalid",
            )
            if (
                permit_document.schema_identifier != PERMITTED_WORK_SCHEMA
                or set(permit_document.values) != {"work"}
                or type(permit_document.values.get("work")) is not str
            ):
                raise RuntimeError("periodic_work_document_invalid")
            if permit_document.values["work"] != work.work_identity:
                continue
            if not self._capacity_has_binding(
                permit.capacity_reference,
                work.binding_reference,
                work.capacity_scope,
            ):
                continue
            if permit.state != "closed" or permit.close_reason != "consumed":
                continue
            if (
                permit.receipt_body_reference is None
                or permit.receipt_reference is None
            ):
                raise RuntimeError("periodic_response_receipt_reference_missing")
            document = self._document(
                permit.receipt_body_reference,
                "periodic_response_receipt_document_invalid",
            )
            if document.schema_identifier not in {
                work.observation_schema,
                PERIODIC_OBSERVATION_INCOMPLETE_SCHEMA,
            }:
                raise RuntimeError("periodic_response_receipt_schema_mismatch")
            matches.append(
                (
                    document,
                    permit.receipt_body_reference,
                    permit.receipt_reference,
                )
            )
        if len(matches) > 1:
            raise RuntimeError("periodic_response_record_duplicate")
        return tuple(matches)

    def _restore_transmission(
        self,
        work: PeriodicWork,
    ) -> AdmittedPeriodicTransmission | AdmittedPeriodicObservationIncomplete | None:
        matches = self._matching_documents(work)
        if not matches:
            return None
        document, body_reference, receipt_reference = matches[0]
        if document.schema_identifier == PERIODIC_OBSERVATION_INCOMPLETE_SCHEMA:
            return self._restore_incomplete(
                work,
                document,
                body_reference,
                receipt_reference,
            )
        try:
            decoded = decode_periodic_transmission(document.values)
        except (TypeError, ValueError) as error:
            raise RuntimeError("periodic_response_receipt_variant_mismatch") from error
        self._validate_candidate(work, decoded.observation.cell)
        if (
            Document(
                work.observation_schema,
                decoded.as_mapping(),
            ).to_bytes()
            != document.to_bytes()
        ):
            raise RuntimeError("periodic_response_receipt_body_mismatch")
        return form_admitted_periodic_transmission(
            work.work_identity,
            decoded,
            body_reference,
            receipt_reference,
        )

    def _restore_polarization(
        self,
        work: PeriodicWork,
    ) -> AdmittedPeriodicPolarization | AdmittedPeriodicObservationIncomplete | None:
        matches = self._matching_documents(work)
        if not matches:
            return None
        document, body_reference, receipt_reference = matches[0]
        if document.schema_identifier == PERIODIC_OBSERVATION_INCOMPLETE_SCHEMA:
            return self._restore_incomplete(
                work,
                document,
                body_reference,
                receipt_reference,
            )
        try:
            decoded = decode_periodic_polarization(document.values)
        except (TypeError, ValueError) as error:
            raise RuntimeError("periodic_response_receipt_variant_mismatch") from error
        self._validate_candidate(work, decoded.observation.cell)
        expected_basis = "x" if work.input_basis == "x linear" else "y"
        if decoded.observation.input_basis != expected_basis:
            raise RuntimeError("periodic_response_receipt_request_mismatch")
        if (
            Document(
                work.observation_schema,
                decoded.as_mapping(),
            ).to_bytes()
            != document.to_bytes()
        ):
            raise RuntimeError("periodic_response_receipt_body_mismatch")
        return form_admitted_periodic_polarization(
            work.work_identity,
            decoded,
            body_reference,
            receipt_reference,
        )

    def _restore_incomplete(
        self,
        work: PeriodicWork,
        document: Document,
        body_reference: Reference,
        receipt_reference: Reference,
    ) -> AdmittedPeriodicObservationIncomplete:
        try:
            outcome = decode_periodic_observation_incomplete(document.values)
        except (TypeError, ValueError) as error:
            raise RuntimeError("periodic_response_receipt_variant_mismatch") from error
        if outcome.work_identity != work.work_identity:
            raise RuntimeError("periodic_response_receipt_request_mismatch")
        if (
            Document(
                PERIODIC_OBSERVATION_INCOMPLETE_SCHEMA,
                outcome.as_mapping(),
            ).to_bytes()
            != document.to_bytes()
        ):
            raise RuntimeError("periodic_response_receipt_body_mismatch")
        return AdmittedPeriodicObservationIncomplete(
            work.work_identity,
            outcome,
            body_reference,
            receipt_reference,
        )

    def _capacity_has_binding(
        self,
        capacity_reference: Reference,
        binding_reference: Reference,
        capacity_scope: str,
    ) -> bool:
        document = self._raw_document(
            capacity_reference,
            "periodic_capacity_document_invalid",
        )
        if (
            document.get("schema_identifier") != "metacraft.authority.capacity"
            or set(document)
            != {
                "limit",
                "qualification_references",
                "schema_identifier",
                "scope",
            }
            or not isinstance(
                document.get("qualification_references"),
                list,
            )
            or document.get("scope") != capacity_scope
        ):
            raise RuntimeError("periodic_capacity_document_invalid")
        qualification_values = document["qualification_references"]
        assert isinstance(qualification_values, list)
        try:
            qualifications = tuple(
                Reference.from_mapping(value) for value in qualification_values
            )
        except (TypeError, ValueError) as error:
            raise RuntimeError("periodic_capacity_document_invalid") from error
        return binding_reference in qualifications

    def _validate_candidate(
        self,
        work: PeriodicWork,
        cell: object,
    ) -> None:
        if (
            getattr(cell, "cell_identity", None) != work.cell_identity
            or getattr(cell, "height_nm", None) != work.height_nm
            or getattr(cell, "geometry", None) != work.geometry
        ):
            raise RuntimeError("periodic_response_receipt_request_mismatch")

    def _document(self, reference: Reference, finding: str) -> Document:
        try:
            return Document.from_bytes(self._session.fetch(reference))
        except (TypeError, ValueError) as error:
            raise RuntimeError(finding) from error

    def _raw_document(
        self,
        reference: Reference,
        finding: str,
    ) -> Mapping[str, object]:
        body = self._session.fetch(reference)
        try:
            decoded = json.loads(body)
            if not isinstance(decoded, dict) or encode_bytes(decoded) != body:
                raise ValueError("periodic_raw_document_invalid")
        except (TypeError, ValueError) as error:
            raise RuntimeError(finding) from error
        return decoded
