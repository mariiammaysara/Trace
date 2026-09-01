"""Stage 2: domain adaptation -- continues fine-tuning FROM Stage 1's
checkpoint on data/sample.mp4's real footage (stage2/prepare_dataset.py +
apply_review.py). The "train" step, kept separate from data prep and
weight export per this phase's explicit requirement.

Usage:
    python training/stage1/train.py && python training/export_weights.py --stage 1
    python training/stage2/prepare_dataset.py   # auto-label with the Stage 1 model
    python training/stage2/apply_review.py      # apply the real, human-reviewed correction
    python training/stage2/train.py             # writes training/runs/detect/stage2_finetune/weights/{best,last}.pt
    python training/export_weights.py --stage 2
"""

from __future__ import annotations

from pathlib import Path

import yaml

STAGE2_DIR = Path(__file__).resolve().parent
CONFIG_PATH = STAGE2_DIR / "config.yaml"
DATASET_PATH = STAGE2_DIR / "dataset.yaml"
RUNS_DIR = STAGE2_DIR.parent / "runs"
RUN_NAME = "stage2_finetune"


def load_config() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def train(config: dict) -> Path:
    from ultralytics import YOLO

    split_dir = STAGE2_DIR.parent / "data" / "stage2" / "split"
    if not (split_dir / "train.txt").exists() or not (split_dir / "val.txt").exists():
        raise FileNotFoundError(
            f"{split_dir} is missing train.txt/val.txt -- run "
            "`python training/stage2/prepare_dataset.py` then `python training/stage2/apply_review.py` first."
        )

    base_weights = (STAGE2_DIR / config["base_weights"]).resolve()
    if not base_weights.exists():
        raise FileNotFoundError(f"{base_weights} not found -- run stage1/train.py then export_weights.py --stage 1 first.")

    augmentation = config.get("augmentation", {})
    model = YOLO(str(base_weights))
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
    print(f"stage2 fine-tuned weights: {best_weights}")


if __name__ == "__main__":
    main()
