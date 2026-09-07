from __future__ import annotations

import pytest
import torch

from experiments.restoration.fixed_measurement.learning.data_contract import (
    RestorationBatch,
    RestorationDataContractError,
    RestorationScene,
)


def test_restoration_scene_preserves_named_data_bus_fields() -> None:
    """
    楠岃瘉鍦烘櫙淇濈暀鍏峰悕鏁版嵁鎬荤嚎瀛楁
    """
    degraded_image = torch.full((1, 8, 8), 0.25, dtype=torch.float32)
    sample = {
        "clean_image": torch.full((1, 8, 8), 0.5, dtype=torch.float32),
        "degraded_image": degraded_image,
        "input_field": torch.sqrt(degraded_image).to(torch.complex64),
        "provenance": {"image_id": "fmd/example/001"},
    }

    scene = RestorationScene.from_sample(sample)

    assert scene.clean_image is sample["clean_image"]
    assert scene.degraded_image is degraded_image
    assert scene.input_field is sample["input_field"]
    assert scene.provenance == {"image_id": "fmd/example/001"}


def test_restoration_scene_requires_degraded_image_by_name() -> None:
    """
    楠岃瘉鍦烘櫙鏄惧紡瑕佹眰閫€鍖栧浘鍍忓瓧娈?    """
    input_image = torch.full((1, 8, 8), 0.25, dtype=torch.float32)
    sample = {
        "clean_image": torch.full((1, 8, 8), 0.5, dtype=torch.float32),
        "input_image": input_image,
        "input_field": torch.sqrt(input_image).to(torch.complex64),
        "provenance": {"image_id": "fmd/example/001"},
    }

    with pytest.raises(
        RestorationDataContractError,
        match="degraded_image is required",
    ):
        RestorationScene.from_sample(sample)


def test_restoration_scene_requires_field_intensity_to_match_degraded_image() -> None:
    """
    楠岃瘉澶嶅満寮哄害涓庨€€鍖栧浘鍍忎竴鑷?    """
    sample = {
        "clean_image": torch.full((1, 8, 8), 0.5, dtype=torch.float32),
        "degraded_image": torch.full((1, 8, 8), 0.25, dtype=torch.float32),
        "input_field": torch.ones((1, 8, 8), dtype=torch.complex64),
        "provenance": {"image_id": "fmd/example/001"},
    }

    with pytest.raises(
        RestorationDataContractError,
        match=r"abs\(input_field\)\^2 must match degraded_image",
    ):
        RestorationScene.from_sample(sample)


def test_restoration_scene_requires_floating_single_channel_images() -> None:
    """
    楠岃瘉澶嶅師鍥惧儚閲囩敤鍗曢€氶亾娴偣寮哄害璇箟
    """
    integer_degraded = torch.zeros((1, 8, 8), dtype=torch.uint8)
    with pytest.raises(RestorationDataContractError, match="floating-point"):
        RestorationScene(
            clean_image=torch.zeros((1, 8, 8), dtype=torch.float32),
            degraded_image=integer_degraded,
            input_field=torch.full(
                (1, 8, 8),
                0.5 + 0.0j,
                dtype=torch.complex64,
            ),
            provenance={"image_id": "integer"},
        )

    multichannel_degraded = torch.full((3, 8, 8), 0.25)
    with pytest.raises(RestorationDataContractError, match="one channel"):
        RestorationScene(
            clean_image=torch.full((3, 8, 8), 0.5),
            degraded_image=multichannel_degraded,
            input_field=torch.sqrt(multichannel_degraded).to(torch.complex64),
            provenance={"image_id": "rgb"},
        )


def test_restoration_batch_is_a_typed_mapping_at_the_training_seam() -> None:
    """
    楠岃瘉璁粌杈圭晫閲囩敤鍏峰悕鎵规绫诲瀷
    """
    degraded_image = torch.full((2, 1, 8, 8), 0.25, dtype=torch.float32)
    collated = {
        "clean_image": torch.full((2, 1, 8, 8), 0.5, dtype=torch.float32),
        "degraded_image": degraded_image,
        "input_field": torch.sqrt(degraded_image).to(torch.complex64),
        "provenance": {"image_id": ["fmd/example/001", "fmd/example/002"]},
        "category": ["one", "two"],
    }

    batch = RestorationBatch.from_collated(collated)

    assert batch.batch_size == 2
    assert batch.degraded_image is degraded_image
    assert batch["input_field"] is collated["input_field"]
    assert batch["category"] == ["one", "two"]


def test_restoration_batch_canonical_mapping_cannot_be_shadowed() -> None:
    """
    楠岃瘉闄勫姞瀛楁涓嶈兘瑕嗙洊瑙勮寖鐗╃悊瀛楁
    """
    degraded_image = torch.full((2, 1, 8, 8), 0.25, dtype=torch.float32)

    with pytest.raises(RestorationDataContractError, match="canonical fields"):
        RestorationBatch(
            clean_image=torch.full((2, 1, 8, 8), 0.5, dtype=torch.float32),
            degraded_image=degraded_image,
            input_field=torch.sqrt(degraded_image).to(torch.complex64),
            provenance={"image_id": ["one", "two"]},
            additional_fields={"degraded_image": torch.zeros_like(degraded_image)},
        )
