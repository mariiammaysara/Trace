"""Data prep for Phase 13's fine-tune -- the "data prep" step, kept
separate from training (train.py) and export (export_weights.py) per this
phase's explicit requirement.

Dataset: Ultralytics' own COCO128 -- the first 128 images of COCO train2017,
officially distributed at
https://github.com/ultralytics/assets/releases/download/v0.0.0/coco128.zip
(~6.7MB, real photographs, real COCO human-annotated labels, standard YOLO
.txt format). Downloaded via ultralytics.data.utils.check_det_dataset(),
which is the same auto-download/verify/extract path `yolo train
data=coco128.yaml` itself uses -- no hand-rolled zip/download logic here.

Ultralytics' own bundled coco128.yaml sets train: and val: to the SAME 128
images (a quickstart shortcut, not a real split) -- using it as-is would make
this phase's before/after comparison meaningless (evaluating a model on the
exact images it just trained on). This script instead builds a genuine,
disjoint, deterministic split.

**Real, measured problem with a naive split, found while building this**:
COCO128 is heavily imbalanced across TRACE's 6 target classes (person: 62
images; bicycle: 3; car: 13; motorcycle: 5; bus: 5; truck: 5 -- out of 128
total). A plain "every Nth image by filename" 80/20 split put ZERO bicycle
and ZERO bus instances in val on the first attempt -- their mAP would have
been undefined, and the before/after comparison for those two classes
literally couldn't have been measured. Fixed with a stratified-minimum-
coverage split: for each of the 6 target classes, the (sorted, so still
deterministic) first image containing it is reserved for val if not already
placed, guaranteeing every class has at least one val instance wherever the
raw data makes that possible at all; the remaining ~20% of val is filled by
the same every-5th-image stride as before. This is a coverage guarantee, not
a result-shaping one -- it does not touch which model does better, only
whether every class can be measured at all.

Usage:
    python training/prepare_dataset.py
"""

from __future__ import annotations

from pathlib import Path

TRAINING_DIR = Path(__file__).resolve().parent
SPLIT_DIR = TRAINING_DIR / "data" / "coco128_split"

VAL_STRIDE = 5  # every VAL_STRIDEth image (by sorted filename) is held out for val

# TRACE's 6 target classes, in COCO's own 80-class numbering (Section 2's
# DEFAULT_CLASS_ALLOWLIST, mapped to the ids coco128's label .txt files use).
TARGET_CLASS_IDS = {0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}


def _download_coco128() -> Path:
    """Returns the local root directory COCO128 was downloaded/extracted
    into (Ultralytics' configured `datasets_dir` -- see `ultralytics.settings`
    -- which in this repo's environment is the repo-root `datasets/`
    directory, gitignored like any other fetched-on-demand asset)."""
    from ultralytics.data.utils import check_det_dataset

    resolved = check_det_dataset("coco128.yaml")
    return Path(resolved["path"])


def _label_classes(labels_dir: Path, image_path: Path) -> set[int]:
    label_path = labels_dir / f"{image_path.stem}.txt"
    with label_path.open(encoding="utf-8") as fh:
        return {int(line.split()[0]) for line in fh if line.strip()}


def build_split(dataset_root: Path) -> tuple[list[Path], list[Path]]:
    """Returns (train_image_paths, val_image_paths), both absolute, sorted,
    disjoint. Only images that actually have a matching label file are
    included (COCO128 ships one .txt per .jpg 1:1, so this should be all of
    them, but this stays honest if that's ever not true).

    See this module's docstring for why this isn't a plain stride: a
    stratified-minimum-coverage pass runs first so every target class gets
    at least one val instance wherever the raw data allows it at all."""
    images_dir = dataset_root / "images" / "train2017"
    labels_dir = dataset_root / "labels" / "train2017"

    images = sorted(images_dir.glob("*.jpg"))
    images = [img for img in images if (labels_dir / f"{img.stem}.txt").exists()]

    val_set: set[Path] = set()
    for class_id in sorted(TARGET_CLASS_IDS):
        if any(class_id in _label_classes(labels_dir, img) for img in val_set):
            continue
        for img in images:
            if class_id in _label_classes(labels_dir, img):
                val_set.add(img)
                break

    for i, img in enumerate(images):
        if i % VAL_STRIDE == VAL_STRIDE - 1:
            val_set.add(img)

    val_images = sorted(val_set)
    train_images = [img for img in images if img not in val_set]
    return train_images, val_images


def _write_list_file(path: Path, images: list[Path]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(str(img) for img in images) + "\n", encoding="utf-8")


def main() -> None:
    dataset_root = _download_coco128()
    train_images, val_images = build_split(dataset_root)

    _write_list_file(SPLIT_DIR / "train.txt", train_images)
    _write_list_file(SPLIT_DIR / "val.txt", val_images)

    print(f"dataset root: {dataset_root}")
    print(f"train images: {len(train_images)} -> {SPLIT_DIR / 'train.txt'}")
    print(f"val images:   {len(val_images)} -> {SPLIT_DIR / 'val.txt'}")


if __name__ == "__main__":
    main()
