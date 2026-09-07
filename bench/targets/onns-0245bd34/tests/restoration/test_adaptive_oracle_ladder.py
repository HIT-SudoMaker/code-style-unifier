from __future__ import annotations

import json

import pytest
import torch

from experiments.restoration.adaptive_measurement.protocol.oracle import (
    OracleLadderConfig,
)
from experiments.restoration.adaptive_measurement.validation.oracle_ladder import (
    run_oracle_ladder,
)


def test_oracle_ladder_writes_a_canonical_limited_evidence_record(
    tmp_path,
) -> None:
    config = OracleLadderConfig(
        project_root=tmp_path,
        array_resolution=(64, 64),
        seed=17,
    )
    result = run_oracle_ladder(config)

    assert result.status == "PASS"
    assert result.metrics["o3_gain_db"] >= 1.0
    assert result.metrics["o2_to_o3_delivery_loss_db"] >= 0.0
    assert result.result_json.is_file()
    assert result.summary_md.is_file()
    assert (result.run_dir / "config.json").is_file()
    assert (result.run_dir / "runtime.json").is_file()
    assert (result.run_dir / "metrics.json").is_file()
    assert (result.run_dir / "checks.json").is_file()
    assert (result.run_dir / "o3_search.pt").is_file()
    observations = torch.load(
        result.run_dir / "observations.pt",
        map_location="cpu",
        weights_only=True,
    )
    assert set(observations) == {"diffraction_limited", "safe", "o1", "o2", "o3"}
    assert observations["o1"]["action_space"] == "arbitrary_complex_transfer"
    assert torch.is_complex(observations["o1"]["processing_transfer"])
    assert observations["o2"]["action_space"] == "ideal_reference_assisted_phase_only"
    assert observations["o3"]["action_space"] == "calibrated_delivered_phase_only"
    assert observations["o3"]["command_phase_radians"].shape == (64, 64)
    assert observations["o3"]["delivered_phase_radians"].shape == (64, 64)
    search_evidence = torch.load(
        result.run_dir / "o3_search.pt",
        map_location="cpu",
        weights_only=True,
    )
    assert search_evidence["schema_version"] == "oracle_ladder_o3_search_v1"
    assert search_evidence["target_observation"]["intensity"].shape == (
        1,
        1,
        64,
        64,
    )
    search_trace = search_evidence["search"]
    assert search_trace["schema_version"] == "delivered_phase_oracle_trace_v1"
    assert len(search_trace["candidates"]) == 85
    selected_candidate = search_trace["candidates"][
        search_trace["selected_candidate_index"]
    ]
    assert (
        selected_candidate["observation"]["observation_id"]
        == search_trace["selected_candidate_observation_id"]
    )
    assert torch.equal(
        selected_candidate["observation"]["command_phase_radians"],
        search_trace["selected_command"]["phase_radians"],
    )
    payload = json.loads(result.result_json.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "adaptive_oracle_ladder_v3"
    assert payload["checks"]["oracle_action_spaces_are_physically_distinct"] is True
    assert payload["oracle_ladder"] == {
        "o1": "arbitrary_complex_transfer",
        "o2": "ideal_reference_assisted_phase_only",
        "o3": "calibrated_delivered_phase_only",
    }
    assert payload["evidence_level"] == "simulation_sanity_check_not_e1_completion"
    assert "does not establish robust E1" in payload["claim_limit"]

    with pytest.raises(FileExistsError, match="immutable"):
        run_oracle_ladder(config)
