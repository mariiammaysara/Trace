"""Stage 1: fine-tune yolov8n on the class-narrowed COCO128 subset
(stage1/prepare_dataset.py) -- the "train" step, kept separate from data
prep and weight export per this phase's explicit requirement. See
stage2/train.py for the domain-adaptation stage that continues from this
stage's output.

Usage:
    python training/stage1/prepare_dataset.py   # once, or to rebuild the dataset
    python training/stage1/train.py             # writes training/runs/detect/stage1_finetune/weights/{best,last}.pt
    python training/export_weights.py --stage 1 # copies best.pt to models/, for YoloDetector to load
"""

from __future__ import annotations

from pathlib import Path

import yaml

STAGE1_DIR = Path(__file__).resolve().parent
CONFIG_PATH = STAGE1_DIR / "config.yaml"
DATASET_PATH = STAGE1_DIR / "dataset.yaml"
RUNS_DIR = STAGE1_DIR.parent / "runs"
RUN_NAME = "stage1_finetune"


def load_config() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def train(config: dict) -> Path:
    from ultralytics import YOLO

    split_dir = STAGE1_DIR.parent / "data" / "stage1" / "split"
    if not (split_dir / "train.txt").exists() or not (split_dir / "val.txt").exists():
        raise FileNotFoundError(f"{split_dir} is missing train.txt/val.txt -- run `python training/stage1/prepare_dataset.py` first.")

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
    print(f"stage1 fine-tuned weights: {best_weights}")


if __name__ == "__main__":
    main()
