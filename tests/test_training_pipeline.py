"""Confirms both stages' pipelines -- prepare -> train -> export -> evaluate
-- run end-to-end without crashing, using tiny REAL dataset slices
(Ultralytics' own coco8: 4 train + 4 val images, genuinely disjoint) --
never the full COCO128/data/sample.mp4 datasets the real stage1/stage2
dataset.yaml files point at, so this stays fast and doesn't require those
downloads/a real multi-epoch run to be present. Skips (not fails) if coco8
can't be downloaded, matching this repo's existing pattern for external-
dependency tests (tests/conftest.py's db_engine fixture).

This is a pipeline smoke test, not an accuracy test: epochs=1 and a tiny
imgsz=64 keep it fast, and it never asserts anything about the resulting
metrics' values -- 4 images can't produce a meaningful accuracy number
either way. Stage 2's test chains from Stage 1's tiny output (a real
checkpoint this test just produced), the same "continue from the previous
stage" structure the real pipeline uses -- not a coincidence, and not
dependent on any pre-existing weights file happening to be present.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

TRAINING_DIR = Path(__file__).resolve().parent.parent / "training"
sys.path.insert(0, str(TRAINING_DIR))

import evaluate as training_evaluate  # noqa: E402
import export_weights as training_export  # noqa: E402


def _load_module(name: str, path: Path):
    # stage1/train.py and stage2/train.py are both literally named train.py
    # -- a plain `import train` would only ever load one of them (Python
    # caches by module name), so each is loaded under a distinct name here.
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


stage1_train = _load_module("stage1_train_module", TRAINING_DIR / "stage1" / "train.py")
stage2_train = _load_module("stage2_train_module", TRAINING_DIR / "stage2" / "train.py")


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


def _tiny_config(base_weights: str) -> dict:
    return {
        "base_weights": base_weights,
        "epochs": 1,
        "imgsz": 64,  # tiny -- this is a smoke test, not an accuracy test
        "batch": 2,
        "lr0": 0.001,
        "optimizer": "auto",
        "patience": 0,
        "seed": 0,
        "augmentation": {"mosaic": 0.0},
    }


def test_stage1_pipeline_runs_end_to_end_on_a_tiny_real_slice(tmp_path, tiny_dataset_yaml, monkeypatch):
    stage1_tmp = tmp_path / "stage1"
    monkeypatch.setattr(stage1_train, "STAGE1_DIR", stage1_tmp / "training" / "stage1")
    monkeypatch.setattr(stage1_train, "DATASET_PATH", tiny_dataset_yaml)
    monkeypatch.setattr(stage1_train, "RUNS_DIR", stage1_tmp / "runs")
    monkeypatch.setattr(stage1_train, "RUN_NAME", "stage1_smoke_test")

    split_dir = stage1_tmp / "training" / "data" / "stage1" / "split"
    split_dir.mkdir(parents=True)
    (split_dir / "train.txt").write_text("placeholder -- this test uses coco8, not the real COCO128 split\n")
    (split_dir / "val.txt").write_text("placeholder -- this test uses coco8, not the real COCO128 split\n")

    best_weights = stage1_train.train(_tiny_config("yolov8n.pt"))
    assert best_weights.exists()
    assert best_weights.name == "best.pt"

    exported_path = tmp_path / "stage1_exported.pt"
    exported = training_export.export(best_weights.parent.parent, exported_path)
    assert exported.exists()

    rows = training_evaluate.evaluate_one(str(exported), tiny_dataset_yaml, "smoke-test")
    assert isinstance(rows, list)  # coco8's 4 val images may or may not contain a TRACE target class -- an empty list is fine


def test_stage2_pipeline_continues_from_stage1_output_on_a_tiny_real_slice(tmp_path, tiny_dataset_yaml, monkeypatch):
    # Produce a real (tiny) Stage 1-shaped checkpoint first -- Stage 2's own
    # config always points base_weights at Stage 1's export, never at a raw
    # pretrained model, so the smoke test should exercise that same chaining,
    # not a shortcut around it.
    stage1_tmp = tmp_path / "stage1_for_stage2"
    monkeypatch.setattr(stage1_train, "STAGE1_DIR", stage1_tmp / "training" / "stage1")
    monkeypatch.setattr(stage1_train, "DATASET_PATH", tiny_dataset_yaml)
    monkeypatch.setattr(stage1_train, "RUNS_DIR", stage1_tmp / "runs")
    monkeypatch.setattr(stage1_train, "RUN_NAME", "stage1_smoke_test")
    split_dir = stage1_tmp / "training" / "data" / "stage1" / "split"
    split_dir.mkdir(parents=True)
    (split_dir / "train.txt").write_text("placeholder\n")
    (split_dir / "val.txt").write_text("placeholder\n")
    stage1_best = stage1_train.train(_tiny_config("yolov8n.pt"))

    stage2_tmp = tmp_path / "stage2"
    monkeypatch.setattr(stage2_train, "STAGE2_DIR", stage2_tmp / "training" / "stage2")
    monkeypatch.setattr(stage2_train, "DATASET_PATH", tiny_dataset_yaml)
    monkeypatch.setattr(stage2_train, "RUNS_DIR", stage2_tmp / "runs")
    monkeypatch.setattr(stage2_train, "RUN_NAME", "stage2_smoke_test")

    split_dir2 = stage2_tmp / "training" / "data" / "stage2" / "split"
    split_dir2.mkdir(parents=True)
    (split_dir2 / "train.txt").write_text("placeholder -- this test uses coco8, not real reviewed footage\n")
    (split_dir2 / "val.txt").write_text("placeholder -- this test uses coco8, not real reviewed footage\n")

    # stage2/train.py resolves base_weights relative to STAGE2_DIR -- an
    # absolute path resolves to itself regardless, same as the real config's
    # relative "../../models/..." path resolves relative to the real STAGE2_DIR.
    best_weights = stage2_train.train(_tiny_config(str(stage1_best)))
    assert best_weights.exists()
    assert best_weights.name == "best.pt"

    exported_path = tmp_path / "stage2_exported.pt"
    exported = training_export.export(best_weights.parent.parent, exported_path)
    assert exported.exists()

    rows = training_evaluate.evaluate_one(str(exported), tiny_dataset_yaml, "smoke-test")
    assert isinstance(rows, list)
