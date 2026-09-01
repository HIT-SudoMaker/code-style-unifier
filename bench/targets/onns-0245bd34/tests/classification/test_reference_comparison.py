from __future__ import annotations

import json
from pathlib import Path

from experiments.classification.reference_comparison import build_d2nn_reference_comparison


def test_build_d2nn_reference_comparison_documents_data_layout_and_model_delta() -> None:
    """
    D2NN 对比内容契约
    """
    comparison = build_d2nn_reference_comparison()

    assert (
        comparison["reference_project"]
        == "reference_projects/project_of_D2NN-with-Pytorch"
    )
    assert comparison["reference_data_root"] == "./data"
    assert comparison["project_data_root"] == "data/raw"
    assert comparison["dataset_alignment"]["classification_dataset"] == "mnist"
    assert comparison["dataset_alignment"]["restoration_sources"] == [
        "BioSR",
        "FMD",
        "BBBC038",
        "targets",
    ]
    assert (
        comparison["model_alignment"]["reference_style"]
        == "notebook-defined D2NN variants"
    )
    assert (
        comparison["model_alignment"]["project_style"]
        == "layered modules with unified data pipeline"
    )


def test_reference_comparison_writes_architecture_table(tmp_path: Path) -> None:
    """
    对比产物契约
    """
    from experiments.classification import reference_comparison

    reference_root = tmp_path / "reference_projects" / "project_of_D2NN-with-Pytorch"
    reference_root.mkdir(parents=True)
    (reference_root / "D2NN.ipynb").write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "source": [
                            "num_layers = 5\n",
                            "distance_between_layers = 15*wl\n",
                            "class Diffractive_Layer: pass\n",
                        ]
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (reference_root / "D2NN-single-layer-FO.ipynb").write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "source": [
                            "num_layers = 1\n",
                            "class Lens_Layer: pass\n",
                            "class Diffractive_Layer: pass\n",
                        ]
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    for topology, accuracy in (("without_lens", 0.87), ("with_lens", 0.86)):
        run_root = tmp_path / "results" / "classification" / topology / "default"
        run_root.mkdir(parents=True)
        (run_root / "final_metrics.json").write_text(
            json.dumps(
                {
                    "evaluation_accuracy": accuracy,
                    "evaluation_split": "val",
                    "test_accuracy": None,
                    "best_val_accuracy": accuracy,
                }
            ),
            encoding="utf-8",
        )
        (run_root / "config.json").write_text(
            json.dumps(
                {
                    "epochs": 50,
                    "batch_size": 200,
                    "learning_rate": 0.002,
                    "weight_decay": 0.0001,
                }
            ),
            encoding="utf-8",
        )
        (run_root / "epoch_metrics.csv").write_text(
            "epoch,seconds\n1,1.5\n2,2.5\n",
            encoding="utf-8",
        )

    summary = reference_comparison.run(project_root=tmp_path)

    output_dir = tmp_path / "results" / "classification" / "reference_comparison"
    table = output_dir / "architecture_comparison.csv"
    benchmark = output_dir / "benchmark_comparison.csv"
    markdown = output_dir / "summary.md"
    assert summary["status"] in {"PASS", "PARTIAL"}
    assert table.exists()
    assert benchmark.exists()
    assert markdown.exists()
    table_content = table.read_text(encoding="utf-8")
    assert "D2NN.ipynb" in table_content
    assert "num_layers=5" in table_content
    assert "Lens_Layer" in table_content
    benchmark_content = benchmark.read_text(encoding="utf-8")
    assert "CURRENT_COMPLETED" in benchmark_content
    assert "0.87 (val)" in benchmark_content
    content = markdown.read_text(encoding="utf-8")
    assert "direct copying is invalid" in content
    assert "Fairness" in content
