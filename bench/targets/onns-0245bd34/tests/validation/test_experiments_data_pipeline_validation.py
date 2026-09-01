from __future__ import annotations


def test_legacy_data_pipeline_validator_has_been_replaced() -> None:
    """
    验证旧data pipeline验证器已迁移到新的分层验证器集合
    """
    from experiments.validation.data import run_data

    validator_names = {
        validator.__name__.rsplit(".", maxsplit=1)[-1]
        for validator in run_data.VALIDATORS
    }
    assert "validate_pipeline" not in validator_names
    assert "validate_stage_contracts" not in validator_names
    assert "validate_raw_sources" in validator_names
    assert "validate_degradation_scenarios" in validator_names
    assert "validate_end_to_end_pipeline" in validator_names
