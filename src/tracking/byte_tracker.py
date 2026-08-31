"""ByteTrack: concrete Tracker wrapping ultralytics' own BYTETracker implementation
(the same code that backs `model.track()`), rather than reimplementing the
Kalman filter + Hungarian matching ourselves. See Section 3 of the study guide
for the build-vs-reuse trade-off this decision was made against.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
from ultralytics.engine.results import Boxes
from ultralytics.trackers.byte_tracker import BYTETracker

from detection.detector import Detection
from tracking.tracker import Track, Tracker

# Boxes() requires an orig_shape, but nothing on the path BYTETracker.update() uses
# (xywh/conf/cls) depends on it -- only the xywhn/xyxyn normalized properties do,
# and this pipeline never calls those. The value is a harmless placeholder.
_UNUSED_ORIG_SHAPE = (1, 1)


class ByteTracker(Tracker):
    """ByteTrack multi-object tracker behind the Tracker interface.

    `track_buffer` is the missed-frame tolerance: how many consecutive frames
    a track can go unmatched (e.g. occlusion) before it's terminated rather
    than recovered under its original object_id. `track_high_thresh` /
    `track_low_thresh` implement ByteTrack's core idea of a two-stage match --
    high-confidence detections are matched first, then remaining unmatched
    tracks get a second chance against low-confidence detections instead of
    discarding them outright.

    Matching is IoU-only (ultralytics' BYTETracker.get_dists), not
    class-aware -- a detection's class never affects which track it's
    assigned to. Real class labels are recovered per-track after matching, by
    looking up the originating Detection via the position ultralytics reports
    it matched (not from anything encoded into the match itself).
    """

    def __init__(
        self,
        track_high_thresh: float = 0.25,
        track_low_thresh: float = 0.1,
        new_track_thresh: float = 0.25,
        track_buffer: int = 30,
        match_thresh: float = 0.8,
        fuse_score: bool = True,
    ) -> None:
        args = SimpleNamespace(
            track_high_thresh=track_high_thresh,
            track_low_thresh=track_low_thresh,
            new_track_thresh=new_track_thresh,
            track_buffer=track_buffer,
            match_thresh=match_thresh,
            fuse_score=fuse_score,
        )
        self._tracker = BYTETracker(args)

    def update(self, detections: list[Detection]) -> list[Track]:
        boxes = self._to_boxes(detections)
        result_rows = self._tracker.update(boxes)

        tracks = []
        for row in result_rows:
            x_min, y_min, x_max, y_max, object_id, score, _cls, source_idx = row
            source = detections[int(source_idx)]
            tracks.append(
                Track(
                    object_id=int(object_id),
                    class_name=source.class_name,
                    bbox=(float(x_min), float(y_min), float(x_max), float(y_max)),
                    confidence=float(score),
                    timestamp=source.timestamp,
                    frame_id=source.frame_id,
                )
            )
        return tracks

    @staticmethod
    def _to_boxes(detections: list[Detection]) -> Boxes:
        if not detections:
            return Boxes(np.zeros((0, 6), dtype=np.float32), orig_shape=_UNUSED_ORIG_SHAPE)
        # [x1, y1, x2, y2, conf, cls] -- cls is a dummy constant (see class docstring:
        # matching is IoU-only, class never factors into it, so any fixed value works).
        rows = [[*det.bbox, det.confidence, 0.0] for det in detections]
        return Boxes(np.array(rows, dtype=np.float32), orig_shape=_UNUSED_ORIG_SHAPE)
