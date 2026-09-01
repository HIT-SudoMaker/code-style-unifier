from __future__ import annotations

import importlib


def test_adaptive_measurement_exposes_only_the_experiment_interface() -> None:
    adaptive = importlib.import_module("experiments.restoration.adaptive_measurement")

    assert tuple(adaptive.__all__) == (
        "AdaptiveEpisodePolicy",
        "AdaptiveEpisodeRequest",
        "AdaptiveEpisodeRecord",
        "run_adaptive_episode",
    )
    for name in adaptive.__all__:
        assert hasattr(adaptive, name)
