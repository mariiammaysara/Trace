"""Fine-tune Phase 2's detector on TRACE-relevant data -- the "train" step,
kept separate from data prep (prepare_dataset.py) and weight export
(export_weights.py) per this phase's explicit requirement.

Reads every hyperparameter from config.yaml (never hardcoded here) and the
dataset from dataset.yaml, so a run is fully reproducible from those two
checked-in files. Requires training/data/coco128_split/{train,val}.txt to
already exist -- run prepare_dataset.py first.

Usage:
    python training/prepare_dataset.py   # once, or whenever you want to rebuild the split
    python training/train.py             # writes training/runs/detect/<name>/weights/{best,last}.pt
    python training/export_weights.py    # copies best.pt to models/, for YoloDetector to load
"""

from __future__ import annotations

from pathlib import Path

import yaml

TRAINING_DIR = Path(__file__).resolve().parent
CONFIG_PATH = TRAINING_DIR / "config.yaml"
DATASET_PATH = TRAINING_DIR / "dataset.yaml"
RUNS_DIR = TRAINING_DIR / "runs"
RUN_NAME = "trace_finetune"


def load_config() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def train(config: dict) -> Path:
    """Runs the fine-tune and returns the path to the best checkpoint this
    run produced."""
    from ultralytics import YOLO

    split_dir = TRAINING_DIR / "data" / "coco128_split"
    if not (split_dir / "train.txt").exists() or not (split_dir / "val.txt").exists():
        raise FileNotFoundError(
            f"{split_dir} is missing train.txt/val.txt -- run `python training/prepare_dataset.py` first."
        )

    augmentation = config.get("augmentation", {})
    model = YOLO(config["base_weights"])
    model.train(
        data=str(DATASET_PATH),
        epochs=config["epochs"],
        imgsz=config["imgsz"],
        batch=config["batch"],
        lr0=config["lr0"],
        optimizer=config.get("optimizer", "auto"),
        patience=config.get("patience", 0),
        seed=config.get("seed", 0),
        project=str(RUNS_DIR / "detect"),
        name=RUN_NAME,
        exist_ok=True,
        verbose=True,
        **augmentation,
    )

    best_weights = RUNS_DIR / "detect" / RUN_NAME / "weights" / "best.pt"
    if not best_weights.exists():
        raise FileNotFoundError(f"training finished but no checkpoint was written to {best_weights}")
    return best_weights


def main() -> None:
    config = load_config()
    best_weights = train(config)
    print(f"fine-tuned weights: {best_weights}")


if __name__ == "__main__":
    main()
