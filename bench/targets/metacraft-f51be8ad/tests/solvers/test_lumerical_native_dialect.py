from __future__ import annotations

from decimal import Decimal
import math
from pathlib import Path
from typing import Any

import pytest

from metacraft.solvers.lumerical_fdtd import session as session_module
from metacraft.solvers.lumerical_fdtd.session import LumericalSession


class _RecordingEngine:
    """
    Record native set/getnamed calls and store values for read-back.

    This fake mirrors the small slice of ``lumapi.FDTD`` that the session
    exercises: object creation, property set, and named property read-back.
    It stores whatever the session translates so inverse reads can run without
    a live engine. ``native = False`` test observations are recorded elsewhere;
    this engine never claims to be a native solve.
    """

    def __init__(self) -> None:
        self.sets: list[tuple[str, Any]] = []
        self.getnamed_calls: list[tuple[str, str]] = []
        self.objects: dict[str, dict[str, Any]] = {}
        self.current: dict[str, Any] = {}
        self.results: dict[tuple[str, str], Any] = {}

    def addfdtd(self) -> None:
        self.current = {}
        self.objects["FDTD"] = self.current

    def addrect(self) -> None:
        self.current = {}

    def addcircle(self) -> None:
        self.current = {}

    def addobject(self, template: str) -> None:
        assert template == "grating_s_params"
        self.current = {}

    def set(self, name: str, value: Any) -> None:
        if name == "name":
            self.objects[value] = self.current
        else:
            self.sets.append((name, value))
            self.current[name] = value

    def getnamed(self, name: str, property_name: str) -> Any:
        self.getnamed_calls.append((name, property_name))
        return self.objects[name][property_name]

    def setnamed(self, name: str, property_name: str, value: Any) -> None:
        self.sets.append((property_name, value))
        self.objects[name][property_name] = value

    def getresult(self, name: str, result_name: str) -> Any:
        return self.results[(name, result_name)]

    def switchtolayout(self) -> None:
        return None

    def deleteall(self) -> None:
        self.objects.clear()
        self.sets.clear()


def _assert_observed(
    engine: _RecordingEngine,
    native_name: str,
    native_value: Any,
) -> None:
    for name, value in engine.sets:
        if name != native_name:
            continue
        if isinstance(native_value, (int, float)) and not isinstance(
            native_value, bool
        ):
            if value == pytest.approx(native_value):
                return
        elif value == native_value:
            return
    raise AssertionError(
        f"native set {native_name!r}->{native_value!r} not observed; "
        f"sets={engine.sets!r}"
    )


# Each row is one (kind, public_name, public_value, native_name, native_value).
# The table mirrors the objects dict emitted by the periodic template in
# ``template/periodic.py`` so the dialect is exercised exhaustively. Every
# native name is sourced from existing evidence (the prior ``_native_property``
# table, the fake-engine tests, the grating_s_params getnamed dump recorded by
# the live qualification probe, and prior tickets 10/15).
_DIALECT_CASES: list[tuple[str, str, Any, str, Any]] = [
    # fdtd solver object
    ("fdtd", "span_x_nm", 660, "x span", 660e-9),
    ("fdtd", "span_y_nm", 660, "y span", 660e-9),
    ("fdtd", "lower_z_nm", -400, "z min", -400e-9),
    ("fdtd", "upper_z_nm", 900, "z max", 900e-9),
    ("fdtd", "lower_x_boundary", "periodic", "x min bc", "Periodic"),
    ("fdtd", "upper_x_boundary", "periodic", "x max bc", "Periodic"),
    ("fdtd", "lower_y_boundary", "periodic", "y min bc", "Periodic"),
    ("fdtd", "upper_y_boundary", "periodic", "y max bc", "Periodic"),
    ("fdtd", "lower_z_boundary", "absorbing", "z min bc", "PML"),
    ("fdtd", "upper_z_boundary", "absorbing", "z max bc", "PML"),
    ("fdtd", "mesh_accuracy", 4, "mesh accuracy", 4),
    ("fdtd", "simulation_time_fs", 1_000, "simulation time", 1e-12),
    (
        "fdtd",
        "autoshutoff_threshold",
        Decimal("0.00001"),
        "auto shutoff min",
        1e-5,
    ),
    # rectangle (substrate and square / rectangular meta-atom)
    ("rectangle", "material", "Si", "material", "Si"),
    ("rectangle", "span_x_nm", 660, "x span", 660e-9),
    ("rectangle", "span_y_nm", 660, "y span", 660e-9),
    ("rectangle", "lower_z_nm", -2_000, "z min", -2_000e-9),
    ("rectangle", "upper_z_nm", 0, "z max", 0.0),
    ("rectangle", "position_x_nm", 0, "x", 0.0),
    ("rectangle", "position_y_nm", 0, "y", 0.0),
    # circle meta-atom
    ("circle", "diameter_nm", 200, "radius", 100e-9),
    ("circle", "material", "Si", "material", "Si"),
    ("circle", "position_x_nm", 0, "x", 0.0),
    ("circle", "position_y_nm", 0, "y", 0.0),
    ("circle", "lower_z_nm", 0, "z min", 0.0),
    ("circle", "upper_z_nm", 500, "z max", 500e-9),
    # ellipse meta-atom
    ("ellipse", "major_axis_nm", 280, "radius", 140e-9),
    ("ellipse", "minor_axis_nm", 160, "radius 2", 80e-9),
    ("ellipse", "material", "Si", "material", "Si"),
    ("ellipse", "position_x_nm", 0, "x", 0.0),
    ("ellipse", "position_y_nm", 0, "y", 0.0),
    ("ellipse", "lower_z_nm", 0, "z min", 0.0),
    ("ellipse", "upper_z_nm", 500, "z max", 500e-9),
    # grating_s_params group
    ("grating_response", "azimuth_degrees", 0, "angle phi", 0),
    ("grating_response", "polar_angle_degrees", 0, "angle theta", 0),
    (
        "grating_response",
        "meta_atom_center_nm",
        250,
        "metamaterial center",
        250e-9,
    ),
    (
        "grating_response",
        "meta_atom_span_nm",
        500,
        "metamaterial span",
        500e-9,
    ),
    (
        "grating_response",
        "polarization_angle_degrees",
        0,
        "polarization angle",
        0,
    ),
    (
        "grating_response",
        "propagation_axis",
        "z",
        "propagation axis",
        "z",
    ),
    (
        "grating_response",
        "propagation_direction",
        "positive",
        "propagation direction",
        1,
    ),
    ("grating_response", "source_offset_nm", 100, "source offset", 100e-9),
    ("grating_response", "source_shape", "plane wave", "source_type", 1),
    (
        "grating_response",
        "start_wavelength_nm",
        633,
        "start wavelength",
        633e-9,
    ),
    ("grating_response", "stop_wavelength_nm", 633, "stop wavelength", 633e-9),
    (
        "grating_response",
        "warnings_suppressed",
        True,
        "suppress_warnings",
        1,
    ),
    (
        "grating_response",
        "target_transmission_order",
        0,
        "target_grating_order_out",
        0,
    ),
    (
        "grating_response",
        "relative_coordinates",
        True,
        "use relative coordinates",
        1,
    ),
    ("grating_response", "span_x_nm", 660, "x span", 660e-9),
    ("grating_response", "span_y_nm", 660, "y span", 660e-9),
    ("grating_response", "position_z_nm", 250, "z", 250e-9),
    ("grating_response", "span_z_nm", 1_100, "z span", 1_100e-9),
]


@pytest.mark.parametrize(
    "kind, public_name, public_value, native_name, native_value",
    _DIALECT_CASES,
)
def test_each_emitted_property_uses_the_exact_native_name_and_round_trips(
    kind: str,
    public_name: str,
    public_value: Any,
    native_name: str,
    native_value: Any,
) -> None:
    engine = _RecordingEngine()
    session = LumericalSession(engine)

    session.create(kind, "object", {public_name: public_value})

    _assert_observed(engine, native_name, native_value)
    # No public unit suffix or underscore form leaks into the native name.
    assert " " + public_name.replace("_", " ").split()[-1] != native_name or (
        not public_name.endswith(("_nm", "_fs"))
    )

    read_back = session.read("object", (public_name,))
    assert read_back == {public_name: public_value}
    object_name = "FDTD" if kind == "fdtd" else "object"
    assert (object_name, native_name) in engine.getnamed_calls


def test_wavelength_properties_do_not_leak_the_unit_suffix() -> None:
    """
    start/stop wavelength must drop the public ``_nm`` suffix at the seam.
    """

    engine = _RecordingEngine()
    session = LumericalSession(engine)
    session.create(
        "grating_response",
        "grating_response",
        {"start_wavelength_nm": 500, "stop_wavelength_nm": 500},
    )
    names = {name for name, _ in engine.sets}
    assert "start wavelength" in names
    assert "stop wavelength" in names
    assert "start wavelength nm" not in names
    assert "stop wavelength nm" not in names


def test_square_maps_as_one_rectangle_with_equal_spans() -> None:
    """
    Squares are rectangular pillars with equal x/y spans.
    """

    engine = _RecordingEngine()
    session = LumericalSession(engine)
    session.create(
        "rectangle",
        "atom",
        {"span_x_nm": 160, "span_y_nm": 160},
    )
    _assert_observed(engine, "x span", 160e-9)
    _assert_observed(engine, "y span", 160e-9)
    assert session.read("atom", ("span_x_nm", "span_y_nm")) == {
        "span_x_nm": 160,
        "span_y_nm": 160,
    }


def test_unknown_object_kind_is_rejected_before_the_engine_call() -> None:
    engine = _RecordingEngine()
    session = LumericalSession(engine)
    with pytest.raises(ValueError, match="native_object_unsupported"):
        session.create("torus", "atom", {"diameter_nm": 200})
    assert engine.sets == []


def test_unknown_property_is_rejected_before_the_engine_call() -> None:
    engine = _RecordingEngine()
    session = LumericalSession(engine)
    with pytest.raises(ValueError, match="native_property_unsupported"):
        session.create(
            "fdtd",
            "solver",
            {"simulation_time_fs": 1_000, "photon_mass_kg": 0},
        )
    assert engine.sets == []


def test_underscore_replacement_fallback_is_absent() -> None:
    """
    A public name whose underscores would previously become spaces must now be
    rejected rather than guessed.
    """

    engine = _RecordingEngine()
    session = LumericalSession(engine)
    with pytest.raises(ValueError, match="native_property_unsupported"):
        session.create(
            "fdtd",
            "solver",
            {"totally_unmodelled_period_fs": 1},
        )
    assert engine.sets == []


def test_unknown_inverse_read_is_rejected_before_the_engine_call() -> None:
    engine = _RecordingEngine()
    session = LumericalSession(engine)
    session.create("fdtd", "solver", {"simulation_time_fs": 1_000})
    engine.getnamed_calls.clear()
    with pytest.raises(ValueError, match="native_read_unsupported"):
        session.read("solver", ("photon_mass_kg",))
    assert engine.getnamed_calls == []


def test_inverse_read_of_uncreated_object_is_rejected_before_the_engine() -> None:
    engine = _RecordingEngine()
    session = LumericalSession(engine)
    with pytest.raises(ValueError, match="native_object_unknown"):
        session.read("ghost", ("simulation_time_fs",))
    assert engine.getnamed_calls == []


def test_reset_clears_the_native_object_registry() -> None:
    """
    After reset, a previously created object is no longer inverse-readable.
    """

    engine = _RecordingEngine()
    session = LumericalSession(engine)
    session.create("fdtd", "solver", {"simulation_time_fs": 1_000})
    engine.getnamed_calls.clear()
    session.reset()
    with pytest.raises(ValueError, match="native_object_unknown"):
        session.read("solver", ("simulation_time_fs",))
    assert engine.getnamed_calls == []


def test_solver_time_extension_round_trips_through_the_native_owner() -> None:
    engine = _RecordingEngine()
    session = LumericalSession(engine)
    session.create(
        "fdtd",
        "solver",
        {
            "autoshutoff_threshold": Decimal("0.00001"),
            "simulation_time_fs": 1_000,
        },
    )

    session.change_maximum_time("solver", 2_000)

    assert engine.objects["FDTD"]["simulation time"] == pytest.approx(2e-12)
    assert ("FDTD", "simulation time") in engine.getnamed_calls


def test_solver_termination_translates_native_decay_evidence() -> None:
    engine = _RecordingEngine()
    session = LumericalSession(engine)
    session.create(
        "fdtd",
        "solver",
        {"autoshutoff_threshold": Decimal("0.00001")},
    )
    engine.results[("FDTD", "status")] = 2
    engine.results[("FDTD", "autoshutoff level")] = {
        "autoshutoff": [1.0, 0.01, 0.000009],
        "t": [1e-15, 500e-15, 875e-15],
    }

    assert session.result("solver", "termination") == {
        "autoshutoff_threshold": pytest.approx(0.00001),
        "native_status": 2,
        "outcome": "autoshutoff",
        "simulated_time_fs": pytest.approx(875),
        "terminal_autoshutoff": pytest.approx(0.000009),
    }


def test_grating_settings_use_the_dump_evidenced_native_spelling() -> None:
    """
    The grating_s_params ``getnamed`` dump (recorded by the live qualification
    probe) reports these three analysis group properties with underscores. The
    dialect must use that exact spelling.
    """

    engine = _RecordingEngine()
    session = LumericalSession(engine)
    session.create(
        "grating_response",
        "grating_response",
        {
            "source_shape": "plane wave",
            "warnings_suppressed": True,
            "target_transmission_order": 0,
        },
    )
    assert ("source_type", 1) in engine.sets
    assert ("suppress_warnings", 1) in engine.sets
    assert ("target_grating_order_out", 0) in engine.sets
    assert session.read(
        "grating_response",
        (
            "source_shape",
            "warnings_suppressed",
            "target_transmission_order",
        ),
    ) == {
        "source_shape": "plane wave",
        "warnings_suppressed": True,
        "target_transmission_order": 0,
    }


_SPECIFIED_POSITION_SETUP_CONTRACT = "\n".join(
    (
        "# METACRAFT_BEGIN_SPECIFIED_POSITION_T",
        'select("T");',
        'set("spatial interpolation", "specified position");',
        "# METACRAFT_END_SPECIFIED_POSITION_T",
    )
)


class _GratingSetupEngine:
    def __init__(
        self,
        *,
        initial_scripts: dict[str, str] | None = None,
        should_apply_setup_contract: bool = True,
    ) -> None:
        self._initial_scripts = initial_scripts or {}
        self.should_apply_setup_contract = should_apply_setup_contract
        self.setup_scripts: dict[str, str] = {}
        self.interpolations: dict[str, str] = {}
        self.parent_named_sets: list[tuple[str, str, object]] = []
        self.constructed_child_mutations: list[
            tuple[str, str, object]
        ] = []
        self.interpolation_reads: list[str] = []
        self.saved_paths: list[str] = []
        self.nearest_after_save: str | None = None
        self.run_count = 0
        self.is_setup = False

    def addobject(self, kind: str) -> None:
        assert kind == "grating_s_params"

    def set(self, name: str, value: object) -> None:
        if name != "name":
            return
        group = str(value)
        self.setup_scripts[group] = self._initial_scripts.get(group, "")
        self.interpolations[group] = "nearest mesh cell"

    def setnamed(
        self,
        name: str,
        property_name: str,
        value: object,
    ) -> None:
        if "::" in name:
            self.constructed_child_mutations.append(
                (name, property_name, value)
            )
            raise RuntimeError(
                "constructed objects not allowed for setnamed operation"
            )
        assert property_name == "setup script"
        self.setup_scripts[name] = str(value)
        self.parent_named_sets.append((name, property_name, value))

    def getnamed(self, name: str, property_name: str) -> object:
        if property_name == "setup script":
            return self.setup_scripts[name]
        if property_name == "spatial interpolation":
            group = name.removesuffix("::T")
            self.interpolation_reads.append(name)
            return self.interpolations[group]
        assert self.is_setup
        if "::" not in name:
            if property_name == "z":
                return -250e-9
            assert property_name == "use relative coordinates"
            return 1
        assert property_name == "z"
        child = name.rsplit("::", 1)[1]
        return {
            "source": -750e-9,
            "R": -650e-9,
            "T": 850e-9,
        }[child]

    def runsetup(self) -> None:
        self.is_setup = True
        if not self.should_apply_setup_contract:
            return
        for group, setup_script in self.setup_scripts.items():
            if _SPECIFIED_POSITION_SETUP_CONTRACT in setup_script:
                self.interpolations[group] = "specified position"

    def save(self, path: str) -> None:
        self.saved_paths.append(path)
        self.runsetup()
        if self.nearest_after_save is not None:
            self.interpolations[self.nearest_after_save] = (
                "nearest mesh cell"
            )

    def run(self) -> None:
        self.run_count += 1


def test_prepare_grating_response_avoids_constructed_child_mutation() -> None:
    engine = _GratingSetupEngine()
    session = LumericalSession(engine)
    session.create("grating_response", "grating_response", {})

    planes = session.prepare_grating_response("grating_response")

    assert engine.constructed_child_mutations == []
    assert engine.parent_named_sets == [
        (
            "grating_response",
            "setup script",
            _SPECIFIED_POSITION_SETUP_CONTRACT,
        )
    ]
    assert planes.as_ipc_mapping() == {
        "reflection_plane_z_nm": -900,
        "source_plane_z_nm": -1_000,
        "transmission_plane_z_nm": 600,
    }


def test_prepare_grating_response_preserves_the_vendor_setup_script() -> None:
    engine = _GratingSetupEngine(
        initial_scripts={"grating_response": "vendor_setup();"}
    )
    session = LumericalSession(engine)
    session.create("grating_response", "grating_response", {})

    session.prepare_grating_response("grating_response")

    assert engine.setup_scripts["grating_response"] == (
        f"vendor_setup();\n{_SPECIFIED_POSITION_SETUP_CONTRACT}"
    )


def test_prepare_grating_response_keeps_an_exact_contract_idempotent() -> None:
    engine = _GratingSetupEngine(
        initial_scripts={
            "grating_response": _SPECIFIED_POSITION_SETUP_CONTRACT,
        }
    )
    session = LumericalSession(engine)
    session.create("grating_response", "grating_response", {})

    first = session.prepare_grating_response("grating_response")
    second = session.prepare_grating_response("grating_response")

    assert first == second
    assert engine.parent_named_sets == []
    assert engine.constructed_child_mutations == []


@pytest.mark.parametrize(
    ("setup_script", "expected_error"),
    (
        (
            "# METACRAFT_BEGIN_SPECIFIED_POSITION_T",
            "grating_setup_contract_incomplete",
        ),
        (
            "# METACRAFT_END_SPECIFIED_POSITION_T",
            "grating_setup_contract_incomplete",
        ),
        (
            "\n".join(
                (
                    _SPECIFIED_POSITION_SETUP_CONTRACT,
                    _SPECIFIED_POSITION_SETUP_CONTRACT,
                )
            ),
            "grating_setup_contract_duplicate",
        ),
        (
            "\n".join(
                (
                    "# METACRAFT_BEGIN_SPECIFIED_POSITION_T",
                    'select("T");',
                    'set("spatial interpolation", "nearest mesh cell");',
                    "# METACRAFT_END_SPECIFIED_POSITION_T",
                )
            ),
            "grating_setup_contract_conflict",
        ),
        (
            "\n".join(
                (
                    "# METACRAFT_END_SPECIFIED_POSITION_T",
                    "# METACRAFT_BEGIN_SPECIFIED_POSITION_T",
                )
            ),
            "grating_setup_contract_conflict",
        ),
    ),
)
def test_prepare_grating_response_rejects_an_invalid_setup_contract(
    setup_script: str,
    expected_error: str,
) -> None:
    engine = _GratingSetupEngine(
        initial_scripts={"grating_response": setup_script}
    )
    session = LumericalSession(engine)
    session.create("grating_response", "grating_response", {})

    with pytest.raises(RuntimeError, match=f"^{expected_error}$"):
        session.prepare_grating_response("grating_response")

    assert engine.parent_named_sets == []
    assert engine.constructed_child_mutations == []


def test_half_nanometre_meta_atom_center_round_trips_exactly() -> None:
    engine = _RecordingEngine()
    session = LumericalSession(engine)
    session.create(
        "grating_response",
        "grating_response",
        {"meta_atom_center_nm": 400.5},
    )

    assert session.read(
        "grating_response",
        ("meta_atom_center_nm",),
    ) == {"meta_atom_center_nm": 400.5}


def test_half_nanometre_converter_normalizes_only_si_representation_noise(
) -> None:
    noisy_half_nanometre_value = math.nextafter(400.5e-9, math.inf)

    assert (
        session_module._from_half_nanometres(noisy_half_nanometre_value)
        == 400.5
    )
    assert session_module._from_half_nanometres(400.6e-9) == pytest.approx(
        400.6
    )


@pytest.mark.parametrize(
    "value",
    (
        None,
        {},
        {
            "reflection_plane_z_nm": -650,
            "source_plane_z_nm": -750,
        },
        {
            "reflection_plane_z_nm": -650,
            "source_plane_z_nm": -750,
            "transmission_plane_z_nm": 850,
            "unexpected": 0,
        },
        {
            "reflection_plane_z_nm": True,
            "source_plane_z_nm": -750,
            "transmission_plane_z_nm": 850,
        },
        {
            "reflection_plane_z_nm": -650,
            "source_plane_z_nm": -750.0,
            "transmission_plane_z_nm": 850,
        },
        {
            "reflection_plane_z_nm": -650,
            "source_plane_z_nm": -750,
            "transmission_plane_z_nm": "850",
        },
    ),
)
def test_grating_response_planes_reject_malformed_ipc(value: object) -> None:
    with pytest.raises(
        RuntimeError,
        match="grating_response_planes_ipc_invalid",
    ):
        session_module._GratingResponsePlanes.from_ipc_mapping(value)


def test_prepare_grating_response_rejects_nearest_mesh_cell_readback() -> None:
    engine = _GratingSetupEngine(should_apply_setup_contract=False)
    session = LumericalSession(engine)
    session.create("grating_response", "grating_response", {})

    with pytest.raises(
        RuntimeError,
        match="grating_transmission_interpolation_mismatch",
    ):
        session.prepare_grating_response("grating_response")

    assert engine.constructed_child_mutations == []


def test_solve_revalidates_every_grating_after_saving_before(
    tmp_path: Path,
) -> None:
    engine = _GratingSetupEngine()
    session = LumericalSession(engine)
    for name in ("first_response", "second_response"):
        session.create("grating_response", name, {})
        session.prepare_grating_response(name)
    engine.interpolation_reads.clear()
    engine.nearest_after_save = "second_response"
    before = (tmp_path / "before.fsp").resolve()
    after = (tmp_path / "after.fsp").resolve()

    with pytest.raises(
        RuntimeError,
        match="^grating_transmission_interpolation_mismatch$",
    ):
        session.solve(before, after)

    assert engine.saved_paths == [str(before)]
    assert engine.interpolation_reads == [
        "first_response::T",
        "second_response::T",
    ]
    assert engine.run_count == 0


def test_solve_runs_only_after_the_saved_construction_reads_back(
    tmp_path: Path,
) -> None:
    engine = _GratingSetupEngine()
    session = LumericalSession(engine)
    session.create("grating_response", "grating_response", {})
    session.prepare_grating_response("grating_response")
    engine.interpolation_reads.clear()
    before = (tmp_path / "before.fsp").resolve()
    after = (tmp_path / "after.fsp").resolve()

    session.solve(before, after)

    assert engine.interpolation_reads == ["grating_response::T"]
    assert engine.run_count == 1
    assert engine.saved_paths == [str(before), str(after)]


def test_public_dialect_names_carry_no_native_spelling() -> None:
    """
    Public MetaCraft names stay natural; vendor spellings live only as the
    native-name value inside the dialect.
    """

    for properties in session_module._NATIVE_DIALECT.values():
        for public_name, entry in properties.items():
            native_name = entry[0]
            assert " " not in public_name
            assert "_" not in native_name or public_name != native_name


def test_dialect_covers_every_template_emitted_kind_and_property() -> None:
    expected = {
        "fdtd": {
            "autoshutoff_threshold",
            "span_x_nm",
            "span_y_nm",
            "lower_z_nm",
            "upper_z_nm",
            "lower_x_boundary",
            "upper_x_boundary",
            "lower_y_boundary",
            "upper_y_boundary",
            "lower_z_boundary",
            "upper_z_boundary",
            "mesh_accuracy",
            "simulation_time_fs",
        },
        "rectangle": {
            "material",
            "span_x_nm",
            "span_y_nm",
            "lower_z_nm",
            "upper_z_nm",
            "position_x_nm",
            "position_y_nm",
        },
        "circle": {
            "diameter_nm",
            "material",
            "position_x_nm",
            "position_y_nm",
            "lower_z_nm",
            "upper_z_nm",
        },
        "ellipse": {
            "major_axis_nm",
            "minor_axis_nm",
            "material",
            "position_x_nm",
            "position_y_nm",
            "lower_z_nm",
            "upper_z_nm",
        },
        "grating_response": {
            "azimuth_degrees",
            "polar_angle_degrees",
            "meta_atom_center_nm",
            "meta_atom_span_nm",
            "polarization_angle_degrees",
            "propagation_axis",
            "propagation_direction",
            "source_offset_nm",
            "source_shape",
            "start_wavelength_nm",
            "stop_wavelength_nm",
            "warnings_suppressed",
            "target_transmission_order",
            "relative_coordinates",
            "span_x_nm",
            "span_y_nm",
            "position_z_nm",
            "span_z_nm",
        },
    }
    for kind, public_names in expected.items():
        assert set(session_module._NATIVE_DIALECT[kind]) == public_names
