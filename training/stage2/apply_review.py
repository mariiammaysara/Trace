"""Applies the human-reviewed correction to Stage 2's auto-labeled frames --
the "apply corrections" step prepare_dataset.py's docstring points to, and
builds the resulting train/val split.

Real review outcome (a real conversation with the user -- see
TRACE_STUDY_GUIDE.md Section 2 for the full record, not summarized away
here): Stage 1's auto-labeling produced ZERO detections on all 30 extracted
frames -- a direct consequence of Stage 1's class collapse (Section 2). The
user reviewed representative frames themselves (early/mid/late in the
clip -- frame_0007, frame_0119, frame_0239, spanning the whole ~16s
recording) against a box I proposed from visual inspection, confirmed it,
and confirmed two things explicitly: (1) this is a near-static scene (same
subject, same camera, same framing throughout -- consistent with Phase 2's
own prior documented observation of this exact clip), so the SAME box
genuinely applies to all 30 frames rather than needing 30 individual
reviews -- not a shortcut taken without asking; (2) the clip is person-only,
no other TRACE target class ever appears in it.

Real, documented consequence of that: Stage 2 only ever adapts the
"person" class to this real footage. The other 5 classes (already
collapsed after Stage 1 -- see Section 2) get zero additional domain-
specific training data here, and continuing to train on person-only labels
risks pushing them toward zero even harder (the model has no counter-
pressure keeping the other classes' weights alive as it specializes
further on "person"). Whether that's what actually happened is answered by
evaluate.py's real 3-way comparison, not assumed here.

This is NOT a generic reusable correction-application tool -- it hardcodes
this one real reviewed outcome, because that's what actually happened. A
future Stage 2 rebuild on different footage needs its own review and its
own version of this script, never a blind rerun of this one.

Usage:
    python training/stage2/apply_review.py
"""

from __future__ import annotations

from pathlib import Path

STAGE2_DIR = Path(__file__).resolve().parent
DATA_DIR = STAGE2_DIR.parent / "data" / "stage2"
IMAGES_DIR = DATA_DIR / "images" / "all"
LABELS_DIR = DATA_DIR / "labels" / "all"
SPLIT_DIR = DATA_DIR / "split"

VAL_STRIDE = 5  # every 5th frame (by frame order) -> val, same convention as stage1

# The reviewed, human-confirmed box (pixel coords in the 640x480 source
# frame): x_min=150, y_min=290, x_max=375, y_max=480, class "person"
# (id 0, matching stage1/dataset.yaml's class order) -- normalized YOLO format.
REVIEWED_LABEL_LINE = "0 0.410156 0.802083 0.351562 0.395833"


def apply_labels() -> list[Path]:
    label_files = sorted(LABELS_DIR.glob("frame_*.txt"))
    if not label_files:
        raise FileNotFoundError(f"no label files in {LABELS_DIR} -- run stage2/prepare_dataset.py first.")
    for label_file in label_files:
        label_file.write_text(REVIEWED_LABEL_LINE + "\n", encoding="utf-8")
    return label_files


def build_split(label_files: list[Path]) -> tuple[list[Path], list[Path]]:
    images = [IMAGES_DIR / f"{lf.stem}.jpg" for lf in label_files]
    train_images = [img for i, img in enumerate(images) if i % VAL_STRIDE != VAL_STRIDE - 1]
    val_images = [img for i, img in enumerate(images) if i % VAL_STRIDE == VAL_STRIDE - 1]
    return train_images, val_images


def _write_list_file(path: Path, images: list[Path]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(str(img) for img in images) + "\n", encoding="utf-8")


def main() -> None:
    label_files = apply_labels()
    print(f"applied reviewed label to {len(label_files)} frames in {LABELS_DIR}")

    train_images, val_images = build_split(label_files)
    _write_list_file(SPLIT_DIR / "train.txt", train_images)
    _write_list_file(SPLIT_DIR / "val.txt", val_images)
    print(f"train images: {len(train_images)} -> {SPLIT_DIR / 'train.txt'}")
    print(f"val images:   {len(val_images)} -> {SPLIT_DIR / 'val.txt'}")


if __name__ == "__main__":
    main()
