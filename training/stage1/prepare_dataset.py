"""Stage 1 data prep: a real COCO subset filtered to TRACE's 6 target
classes (person, car, motorcycle, bus, truck, bicycle) -- not just "some
COCO images that happen to include these classes among 80," a genuine
class-narrowed retrain. This is the standard, reproducible baseline
improvement step before Stage 2's domain adaptation (stage2/prepare_dataset.py).

Source: Ultralytics' own COCO128 (first 128 images of COCO train2017), same
real download as before
(https://github.com/ultralytics/assets/releases/download/v0.0.0/coco128.zip,
~6.7MB) via ultralytics.data.utils.check_det_dataset().

Why a full copy of the dataset tree, not just new label files: Ultralytics
derives a label file's path from its image's path by replacing the
`/images/` path segment with `/labels/` (ultralytics.data.utils.
img2label_paths -- confirmed by reading that function's source, not
assumed). Since the remapped/filtered labels must live somewhere OTHER than
COCO128's own `labels/train2017/` (overwriting the original download in
place would be destructive and would corrupt it for any other future use),
this script copies the 128 images into a new `images/train2017/` tree next
to a new `labels/train2017/` tree carrying the remapped labels -- so the
`/images/` -> `/labels/` substitution resolves to OUR labels, and the
original `datasets/coco128/` stays untouched.

Class remapping (COCO's original 80-class ids -> TRACE's 0-indexed 6):
    COCO id  0 (person)     -> 0
    COCO id  2 (car)        -> 1
    COCO id  3 (motorcycle) -> 2
    COCO id  5 (bus)        -> 3
    COCO id  7 (truck)      -> 4
    COCO id  1 (bicycle)    -> 5
matching src/detection/yolo_detector.py's DEFAULT_CLASS_ALLOWLIST order
exactly, so the class NAME everywhere else in this codebase and the class
INDEX this model predicts stay obviously aligned to a reader.

All 128 images are kept (not just the ones containing a target class):
images with zero target-class instances become legitimate background
training data (an empty label file) -- standard practice, and directly
useful for TRACE, which cares about not spuriously boxing irrelevant scenes
(Section 2's "no false positives on background" observed limitation).

Held-out split: same stratified-minimum-coverage approach as before (every
5th image by sorted filename -> val, plus one extra image per class
reserved for val if that class would otherwise have zero val instances) --
see build_split()'s docstring for why the naive version isn't good enough.

Usage:
    python training/stage1/prepare_dataset.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

STAGE1_DIR = Path(__file__).resolve().parent
DATA_DIR = STAGE1_DIR.parent / "data" / "stage1"
IMAGES_DIR = DATA_DIR / "images" / "train2017"
LABELS_DIR = DATA_DIR / "labels" / "train2017"
SPLIT_DIR = DATA_DIR / "split"

VAL_STRIDE = 5

# COCO's original 80-class id -> TRACE's 0-indexed 6-class id, matching
# src/detection/yolo_detector.py's DEFAULT_CLASS_ALLOWLIST order exactly.
COCO_TO_TRACE_CLASS_ID = {0: 0, 2: 1, 3: 2, 5: 3, 7: 4, 1: 5}
TRACE_CLASS_NAMES = ["person", "car", "motorcycle", "bus", "truck", "bicycle"]


def _download_coco128() -> Path:
    from ultralytics.data.utils import check_det_dataset

    resolved = check_det_dataset("coco128.yaml")
    return Path(resolved["path"])


def _filter_and_remap_label_file(src_path: Path) -> str:
    """Returns the new label file's text content: only lines for TRACE's 6
    target classes, class id remapped -- '' (no lines) if the image has none
    of them, which is a legitimate empty label file (background image)."""
    kept_lines = []
    with src_path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            parts = line.split()
            coco_class_id = int(parts[0])
            if coco_class_id in COCO_TO_TRACE_CLASS_ID:
                new_class_id = COCO_TO_TRACE_CLASS_ID[coco_class_id]
                kept_lines.append(" ".join([str(new_class_id), *parts[1:]]))
    return "\n".join(kept_lines) + ("\n" if kept_lines else "")


def build_stage1_dataset(coco128_root: Path) -> None:
    """Copies all 128 COCO128 images + writes filtered/remapped labels into
    DATA_DIR's own images/labels tree (see this module's docstring for why
    a copy, not a reference into datasets/coco128/ directly)."""
    src_images_dir = coco128_root / "images" / "train2017"
    src_labels_dir = coco128_root / "labels" / "train2017"

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    LABELS_DIR.mkdir(parents=True, exist_ok=True)

    for src_image in sorted(src_images_dir.glob("*.jpg")):
        src_label = src_labels_dir / f"{src_image.stem}.txt"
        if not src_label.exists():
            continue
        shutil.copy2(src_image, IMAGES_DIR / src_image.name)
        (LABELS_DIR / f"{src_image.stem}.txt").write_text(_filter_and_remap_label_file(src_label), encoding="utf-8")


def _label_classes(image_path: Path) -> set[int]:
    label_path = LABELS_DIR / f"{image_path.stem}.txt"
    if not label_path.exists() or label_path.stat().st_size == 0:
        return set()
    with label_path.open(encoding="utf-8") as fh:
        return {int(line.split()[0]) for line in fh if line.strip()}


def build_split() -> tuple[list[Path], list[Path]]:
    """Same stratified-minimum-coverage split as the original (pre-Stage-1)
    prepare_dataset.py: a plain "every 5th image" split can leave a rare
    class with zero val instances (found for real, for `bicycle`/`bus`, when
    this was first built) -- so one image per class is reserved for val
    first (if not already covered), then the rest of val is filled by
    stride. Deterministic (no random seed)."""
    images = sorted(IMAGES_DIR.glob("*.jpg"))

    val_set: set[Path] = set()
    for class_id in range(len(TRACE_CLASS_NAMES)):
        if any(class_id in _label_classes(img) for img in val_set):
            continue
        for img in images:
            if class_id in _label_classes(img):
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


def _write_baseline_val_list(val_images: list[Path], coco128_root: Path) -> Path:
    """The pretrained baseline is an 80-class COCO model -- evaluating it
    fairly means pointing it at the SAME val images but through their
    ORIGINAL coco128 path (so /images/->/labels/ resolves to coco128's own
    unmodified 80-class labels, not this dataset's 6-class-remapped ones;
    see evaluate.py for why mixing the two class spaces in one dataset.yaml
    would silently misalign class indices between the two models)."""
    original_paths = [coco128_root / "images" / "train2017" / img.name for img in val_images]
    path = SPLIT_DIR / "val_original_coco_paths.txt"
    _write_list_file(path, original_paths)
    return path


def main() -> None:
    coco128_root = _download_coco128()
    build_stage1_dataset(coco128_root)
    train_images, val_images = build_split()

    _write_list_file(SPLIT_DIR / "train.txt", train_images)
    _write_list_file(SPLIT_DIR / "val.txt", val_images)
    baseline_val_path = _write_baseline_val_list(val_images, coco128_root)

    print(f"coco128 source: {coco128_root}")
    print(f"stage1 dataset: {DATA_DIR}")
    print(f"train images: {len(train_images)} -> {SPLIT_DIR / 'train.txt'}")
    print(f"val images:   {len(val_images)} -> {SPLIT_DIR / 'val.txt'}")
    print(f"baseline-eval val list (original coco128 paths, 80-class labels): {baseline_val_path}")


if __name__ == "__main__":
    main()
