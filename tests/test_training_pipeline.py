"""Confirms training/train.py -> export_weights.py -> evaluate.py runs
end-to-end without crashing, using a tiny REAL dataset slice (Ultralytics'
own coco8: 4 train + 4 val images, genuinely disjoint) -- never the full
COCO128 dataset training/dataset.yaml points at, so this test stays fast and
doesn't require that ~7MB download + a real multi-epoch training run to be
present. Skips (not fails) if coco8 can't be downloaded, matching this
repo's existing pattern for external-dependency tests (tests/conftest.py's
db_engine fixture).

This is a pipeline smoke test, not an accuracy test: epochs=1 and a tiny
imgsz=64 keep it fast: this only asserts the pipeline PRODUCES a checkpoint
and doesn't crash, never asserting anything about the resulting metrics'
values (4 images can't produce a meaningful accuracy number either way).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "training"))

import evaluate as training_evaluate  # noqa: E402
import export_weights as training_export  # noqa: E402
import train as training_train  # noqa: E402


@pytest.fixture
def tiny_dataset_yaml(tmp_path):
    from ultralytics.data.utils import check_det_dataset

    try:
        resolved = check_det_dataset("coco8.yaml")
    except Exception as exc:  # network/download failure -- not a pipeline bug
        pytest.skip(f"coco8 dataset not reachable/downloadable: {exc}")

    names_block = "\n".join(f"  {class_id}: {name}" for class_id, name in resolved["names"].items())
    dataset_yaml = tmp_path / "tiny_dataset.yaml"
    dataset_yaml.write_text(f"train: {resolved['train']}\nval: {resolved['val']}\nnames:\n{names_block}\n", encoding="utf-8")
    return dataset_yaml


@pytest.fixture
def tiny_config() -> dict:
    return {
        "base_weights": "yolov8n.pt",
        "epochs": 1,
        "imgsz": 64,  # tiny -- this is a smoke test, not an accuracy test
        "batch": 2,
        "lr0": 0.001,
        "optimizer": "auto",
        "patience": 0,
        "seed": 0,
        "augmentation": {"mosaic": 0.0},
    }


def test_training_pipeline_runs_end_to_end_on_a_tiny_real_slice(tmp_path, tiny_dataset_yaml, tiny_config, monkeypatch):
    # Point train.py's module-level paths at a scratch dataset/run dir for
    # this test, and its own tiny (coco8) split, instead of the real
    # COCO128-derived training/data/coco128_split/. All are read fresh from
    # module scope at call time, so patching them here is enough -- no
    # change to train.py itself.
    monkeypatch.setattr(training_train, "TRAINING_DIR", tmp_path)
    monkeypatch.setattr(training_train, "DATASET_PATH", tiny_dataset_yaml)
    monkeypatch.setattr(training_train, "RUNS_DIR", tmp_path / "runs")
    monkeypatch.setattr(training_train, "RUN_NAME", "pipeline_smoke_test")

    split_dir = tmp_path / "data" / "coco128_split"
    split_dir.mkdir(parents=True)
    (split_dir / "train.txt").write_text("placeholder -- this test uses coco8, not the real split\n")
    (split_dir / "val.txt").write_text("placeholder -- this test uses coco8, not the real split\n")

    best_weights = training_train.train(tiny_config)
    assert best_weights.exists()
    assert best_weights.name == "best.pt"

    exported_path = tmp_path / "exported.pt"
    exported = training_export.export(best_weights.parent.parent, exported_path)
    assert exported.exists()

    monkeypatch.setattr(training_evaluate, "DATASET_PATH", tiny_dataset_yaml)
    rows = training_evaluate.evaluate_one(str(exported), "smoke-test")
    assert isinstance(rows, list)  # coco8's 4 images may or may not contain a TRACE target class -- an empty list is fine
