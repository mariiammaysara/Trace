"""Open a video source (file path or camera index) and print frame_id + timestamp
for the first N frames, so FrameSource's output can be sanity-checked visually.

Usage:
    python scripts/preview_frames.py path/to/video.mp4
    python scripts/preview_frames.py 0 --num-frames 20 --frame-skip 2
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from detection.frame_source import FrameSource


def _parse_source(raw: str) -> str | int:
    """A source that looks like a bare integer is a camera index; anything else is a file path."""
    try:
        return int(raw)
    except ValueError:
        return raw


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="video file path or camera index (e.g. 0)")
    parser.add_argument("--num-frames", type=int, default=10, help="frames to print (default: 10)")
    parser.add_argument("--frame-skip", type=int, default=1, help="process every Nth frame (default: 1)")
    parser.add_argument("--source-id", default=None, help="label to tag frames with (default: source)")
    args = parser.parse_args()

    source = _parse_source(args.source)
    with FrameSource(source, source_id=args.source_id, frame_skip=args.frame_skip) as frame_source:
        print(f"opened source={source!r} is_live={frame_source.is_live} frame_skip={frame_source.frame_skip}")
        for i in range(args.num_frames):
            frame = frame_source.read()
            if frame is None:
                print(f"source exhausted after {i} frame(s)")
                break
            print(
                f"frame_id={frame.frame_id:>5}  timestamp={frame.timestamp:.3f}s  "
                f"shape={frame.image.shape}  source_id={frame.source_id}"
            )


if __name__ == "__main__":
    main()
