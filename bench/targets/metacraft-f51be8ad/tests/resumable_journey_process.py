from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path

import metacraft.command as command_module
import metacraft.science.metalens.conduct as metalens_conduct
import metacraft.solvers.lumerical_fdtd.artifacts as artifacts_module
import metacraft.solvers.lumerical_fdtd.periodic_response as periodic_response_module
import metacraft.solvers.lumerical_fdtd.probe as probe_module
import metacraft.solvers.lumerical_fdtd.qualification as qualification_module
import metacraft.work_execution as work_execution_module
from metacraft.authority.session import AuthoritySession
from metacraft.field.fast_debye import CZTDebyeRealization, FFTDebyeRealization
from metacraft.science.metalens.brief import MetalensBrief
from metacraft.solvers.lumerical_fdtd import LumericalConfig
from metacraft.solvers.lumerical_fdtd.project_execution import ProjectExecution
from metacraft.solvers.lumerical_fdtd.qualification import (
    PERIODIC_POLARIZATION_RESPONSE,
    PERIODIC_REFERENCE_SURFACE_RESPONSE,
    PERIODIC_TRANSMISSION_RESPONSE,
    PeriodicResponseProof,
    PeriodicResponseQualification,
)
from tests.lumerical_fixtures import jones_response
import tests.propagation_fixtures as propagation_fixtures
from tests.propagation_fixtures import fake_metalens_ports
from tests.reference_surface_fakes import bounded_reference_surface
from tests.solver_fakes import FakeSession


class _Patch:
    def setattr(self, target: object, name: str, value: object) -> None:
        setattr(target, name, value)


class _PoisonEvidenceAdapter:
    def open(self, **_keywords: object) -> object:
        raise AssertionError("terminal_replay_opened_evidence_adapter")


_DURABLE_RECEIPT_EXIT = 75


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--journey-evidence",
        choices=(
            "none",
            "recorded",
            "recorded-interrupt-after-receipt",
            "poison",
        ),
    )
    parser.add_argument("--brief", type=Path, required=True)
    parser.add_argument("--application-root", type=Path, required=True)
    parser.add_argument("--material-library", type=Path, required=True)
    parser.add_argument("--answer", type=Path)
    parser.add_argument("--journey-instant", required=True)
    parser.add_argument("--lumerical-environment", type=Path)
    selected = parser.parse_args(arguments)
    brief = MetalensBrief.decode_canonical_bytes(selected.brief.read_bytes())
    _configure_bounded_calculations()
    _freeze_journey_clock(datetime.fromisoformat(selected.journey_instant))
    if selected.journey_evidence in {
        "recorded",
        "recorded-interrupt-after-receipt",
    }:
        adapter = _fake_adapter(brief, selected.application_root)
        if selected.journey_evidence == "recorded-interrupt-after-receipt":
            _interrupt_after_durable_receipt()
    elif selected.journey_evidence == "poison":
        _poison_propagation()
        adapter = _PoisonEvidenceAdapter()
    else:
        adapter = None
    command_module._compose_evidence_adapter = (  # type: ignore[attr-defined]
        lambda _path, *, material_library: adapter
    )
    forwarded = [
        "conduct",
        "--brief",
        str(selected.brief),
        "--application-root",
        str(selected.application_root),
        "--material-library",
        str(selected.material_library),
    ]
    if selected.answer is not None:
        forwarded.extend(("--answer", str(selected.answer)))
    if selected.lumerical_environment is not None:
        forwarded.extend(
            ("--lumerical-environment", str(selected.lumerical_environment))
        )
    return command_module.main(forwarded)


def _fake_adapter(
    brief: MetalensBrief,
    application_root: Path,
) -> object:
    patch = _Patch()
    original_config = propagation_fixtures.lumerical_config

    def reusable_config(path: Path) -> LumericalConfig:
        executable = path / "Lumerical" / "bin" / "fdtd-solutions.exe"
        if not executable.is_file():
            return original_config(path)
        return LumericalConfig(
            executable=executable,
            python_api=path / "Lumerical" / "api" / "python" / "lumapi.py",
            license_utility=(
                path / "licensingclient" / "winx64" / "lmutil.exe"
            ),
            license_server="fixture-license",
            freshness_seconds=300,
            runs_directory=path / "runs",
        )

    patch.setattr(propagation_fixtures, "lumerical_config", reusable_config)
    native_result = FakeSession.result

    def routed_result(
        session: FakeSession,
        name: str,
        result_name: str,
    ) -> dict[str, object]:
        if result_name == "linear_transmission":
            return dict(jones_response(session._objects))
        if result_name == "reference_surface":
            return bounded_reference_surface(session)
        return dict(native_result(session, name, result_name))

    patch.setattr(FakeSession, "result", routed_result)
    _record_fake_solves(application_root)
    proof = _response_proof()
    return fake_metalens_ports(
        brief,
        application_root.parent / "fixture-adapter",
        patch,
        response_proof=proof,
    )["evidence_adapter"]


def _record_fake_solves(application_root: Path) -> None:
    original = FakeSession.solve
    ledger = application_root.parent / "fixture-adapter" / "solve-ledger.jsonl"

    def solve(session: FakeSession, before: Path, after: Path) -> ProjectExecution:
        execution = original(session, before, after)
        record = json.dumps(
            {
                "after": after.name,
                "before": before.name,
                "work": before.parent.name,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode() + b"\n"
        ledger.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(ledger, os.O_APPEND | os.O_CREAT | os.O_WRONLY)
        try:
            os.write(descriptor, record)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return execution

    FakeSession.solve = solve  # type: ignore[method-assign]


def _freeze_journey_clock(fixed_now: datetime) -> None:
    if fixed_now.tzinfo is None:
        raise ValueError("journey_instant_timezone_missing")
    fixed_now = fixed_now.astimezone(UTC)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz: object = None) -> datetime:
            del tz
            return fixed_now

    for module in (
        propagation_fixtures,
        periodic_response_module,
        probe_module,
        qualification_module,
        artifacts_module,
        work_execution_module,
    ):
        if hasattr(module, "datetime"):
            setattr(module, "datetime", FixedDateTime)


def _response_proof() -> PeriodicResponseProof:

    def qualification(response_kind: str, is_available: bool):
        return (
            PeriodicResponseQualification.qualified(response_kind)
            if is_available
            else PeriodicResponseQualification.response_not_returned(response_kind)
        )

    return PeriodicResponseProof(
        response_qualifications=(
            qualification(PERIODIC_TRANSMISSION_RESPONSE, True),
            qualification(PERIODIC_POLARIZATION_RESPONSE, True),
            qualification(
                PERIODIC_REFERENCE_SURFACE_RESPONSE,
                True,
            ),
        )
    )


def _interrupt_after_durable_receipt() -> None:
    original = AuthoritySession.admit_receipt
    has_interrupted = False

    def admit_then_interrupt(
        session: AuthoritySession,
        document: object,
        *,
        permit_reference: object,
    ) -> object:
        nonlocal has_interrupted
        decision = original(
            session,
            document,  # type: ignore[arg-type]
            permit_reference=permit_reference,  # type: ignore[arg-type]
        )
        has_open_sibling = any(
            permit.state == "open" for permit in session.observe().permits
        )
        if not has_interrupted and not has_open_sibling:
            has_interrupted = True
            os._exit(_DURABLE_RECEIPT_EXIT)
        return decision

    AuthoritySession.admit_receipt = admit_then_interrupt  # type: ignore[method-assign]


def _configure_bounded_calculations() -> None:
    metalens_conduct.observe_czt_debye = (  # type: ignore[assignment]
        lambda: CZTDebyeRealization(device="cpu", pupil_samples=65)
    )
    metalens_conduct.observe_fft_debye = (  # type: ignore[assignment]
        lambda: FFTDebyeRealization(device="cpu", pupil_samples=65)
    )


def _poison_propagation() -> None:
    def fail(*_arguments: object, **_keywords: object) -> object:
        raise AssertionError("terminal_replay_called_propagation")

    metalens_conduct._propagate_field = fail  # type: ignore[attr-defined]


if __name__ == "__main__":
    raise SystemExit(main())
