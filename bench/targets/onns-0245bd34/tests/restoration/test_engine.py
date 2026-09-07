from __future__ import annotations

import torch
from torch.utils.data import DataLoader

from experiments.restoration.fixed_measurement.learning.backend import BackendConfig
from experiments.restoration.fixed_measurement.learning.config import TrainingConfig
from experiments.restoration.fixed_measurement.learning.engine import GradientAccumulationState, run_epoch


def test_run_epoch_carries_the_final_partial_effective_batch() -> None:
    """
    楠岃瘉涓嶈兘鍥犳牱鏈暟鏃犳硶鏁撮櫎鏈夋晥鎵归噺鑰屼涪寮冧竴杞湯灏剧殑璁粌鏍锋湰
    """
    samples = [
        {
            "clean_image": torch.full((1, 4, 4), 0.75),
            "degraded_image": torch.full((1, 4, 4), 0.25),
        }
        for _ in range(10)
    ]
    loader = DataLoader(samples, batch_size=2, shuffle=False)
    model = torch.nn.Conv2d(1, 1, kernel_size=1, bias=False)
    optimizer = torch.optim.SGD(model.parameters(), lr=0.1)
    config = TrainingConfig(
        model_role="backend_only",
        backend=BackendConfig(model_name="nafnet_s"),
        trainable_parameters=("backend",),
        batch_size=2,
        effective_batch_size=8,
        loss_ssim_weight=0.0,
        loss_frequency_weight=0.0,
    )

    accumulation = GradientAccumulationState()
    first_row = run_epoch(
        model,
        loader,
        config,
        torch.device("cpu"),
        epoch=1,
        split="train",
        optimizer=optimizer,
        operating_point_hash="geometry-hash",
        gradient_accumulation=accumulation,
    )

    assert first_row["optimizer_updates"] == 1
    assert accumulation.pending_samples == 2

    second_row = run_epoch(
        model,
        loader,
        config,
        torch.device("cpu"),
        epoch=2,
        split="train",
        optimizer=optimizer,
        operating_point_hash="geometry-hash",
        optimizer_update_start=1,
        optimizer_update_limit=2,
        gradient_accumulation=accumulation,
    )

    assert second_row["optimizer_updates"] == 2
    assert accumulation.pending_samples == 0
