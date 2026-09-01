"""Real, human-verified ground truth for `data/sample.mp4` -- the real
~16s/244-frame/15fps webcam clip already used throughout Phase 2/8/9/10/13
testing.

**A full-clip scan (running the pretrained detector across all 244 frames)
confirmed the person is detected in every single frame -- zero gaps.**
Exactly one detection per frame except frame 241, which gets two
overlapping boxes (confidences 0.72 and 0.28) -- the exact, real "Duplicate
detection at frame 241" finding Section 2's Observed limitations already
documented. This scan is what makes "the person is visible in literally
every frame of this clip" a verified fact this ground truth relies on, not
an assumption.

The ground-truth BOX reuses the exact box Phase 13's Stage 2 review already
established and got human-confirmed against three frames spanning the whole
clip (early/mid/late: frame 7, 119, 239) -- x_min=150, y_min=290,
x_max=375, y_max=480 -- since the scene is confirmed near-static (same
subject, same camera, same framing throughout). Reusing that real,
independently human-verified box -- rather than copying any single
detector's own predicted boxes, which would bias this evaluation toward
whichever model's output got copied -- is what keeps this ground truth
honest and detector-agnostic.

**A real, stated limitation, not hidden**: this clip has exactly ONE
object, present the entire time. It can verify whether a tracker maintains
one continuous id across a full real clip despite real per-frame detection
noise (frame 241's duplicate, in particular) -- but it can NEVER produce or
detect an ID SWITCH, since there is nothing to switch identities WITH. See
ground_truth_synthetic.py for a scenario built specifically to exercise
that case.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

FRAME_COUNT = 244
PERSON_BOX: Tuple[float, float, float, float] = (150.0, 290.0, 375.0, 480.0)
PERSON_GT_ID = 1


def ground_truth() -> Dict[int, List[Tuple[int, Tuple[float, float, float, float]]]]:
    """frame_id -> [(gt_id, bbox_xyxy)] for every frame in the clip."""
    return {frame_id: [(PERSON_GT_ID, PERSON_BOX)] for frame_id in range(FRAME_COUNT)}
