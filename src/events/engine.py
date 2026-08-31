"""EventEngine: the full Phase 7 pipeline stage.

Wires FrameSource -> Detector -> Tracker output into Phases 4-6 (Trajectory,
Geometry) internally, and runs every Section 7 rule against their combined
output each frame, producing structured Events. Pure/deterministic -- no LLM
or other nondeterministic call anywhere in this module or any rule module it
drives (a hard constraint: the study guide's engineering rules require the
LLM to reason over structured data this layer produces, never the reverse).

update() takes `timestamp` as an explicit argument, separately from `tracks`,
unlike Tracker/TrajectoryManager which only need the tracks list. This is
necessary, not incidental: OBJECT_DISAPPEARED must keep advancing its
missing-time bookkeeping on frames where zero objects are currently tracked,
and there is no way to recover "what time is it now" from an empty tracks
list. Call update() once per frame, in order, every frame -- including empty
ones -- same contract as every stateful component it wraps.
"""

from __future__ import annotations

from typing import List, Optional

from events.event import Event
from events.line_crossed import build_event as build_line_crossed_event
from events.loitering import LoiteringRule
from events.object_appeared import ObjectAppearedRule
from events.object_disappeared import ObjectDisappearedRule
from events.overspeed import OverspeedRule
from events.stopped import StoppedRule
from events.sudden_stop import SuddenStopRule
from events.zone_entered import build_event as build_zone_entered_event
from events.zone_exited import build_event as build_zone_exited_event
from geometry.homography import GroundPlaneHomography
from geometry.line_crossing import Line, LineCrossingDetector
from geometry.speed import SpeedEstimator
from geometry.zone import Zone, ZoneDetector
from tracking.tracker import Track
from trajectories.dwell import DwellTracker
from trajectories.trajectory import TrajectoryManager, centroid


class EventEngine:
    def __init__(
        self,
        camera_id: str,
        homography: GroundPlaneHomography,
        lines: Optional[List[Line]] = None,
        zones: Optional[List[Zone]] = None,
        *,
        stationary_speed_threshold: float = 30.0,
        zone_debounce_frames: int = 3,
        speed_limit: float = 5.0,
        overspeed_smoothing_window: int = 3,
        min_stationary_seconds: float = 2.0,
        min_deceleration_magnitude: float = 500.0,
        min_dwell_seconds: float = 5.0,
        missing_timeout_seconds: float = 2.0,
    ) -> None:
        self.camera_id = camera_id
        zones = list(zones) if zones else []

        self._trajectory_manager = TrajectoryManager(stationary_speed_threshold=stationary_speed_threshold)
        self._speed_estimator = SpeedEstimator(homography)
        self._line_detector = LineCrossingDetector(list(lines) if lines else [])
        self._zone_detector = ZoneDetector(zones, debounce_frames=zone_debounce_frames)
        self._zone_ids = [zone.id for zone in zones]
        self._dwell_tracker = DwellTracker()

        self._overspeed_rule = OverspeedRule(speed_limit, window=overspeed_smoothing_window, camera_id=camera_id)
        self._stopped_rule = StoppedRule(min_stationary_seconds, camera_id=camera_id)
        self._sudden_stop_rule = SuddenStopRule(min_deceleration_magnitude, camera_id=camera_id)
        self._loitering_rule = LoiteringRule(min_dwell_seconds, camera_id=camera_id)
        self._appeared_rule = ObjectAppearedRule(camera_id=camera_id)
        self._disappeared_rule = ObjectDisappearedRule(missing_timeout_seconds, camera_id=camera_id)

    def update(self, tracks: List[Track], timestamp: float) -> List[Event]:
        events: List[Event] = []

        for track in tracks:
            appeared = self._appeared_rule.update(track)
            if appeared is not None:
                events.append(appeared)

        events.extend(self._disappeared_rule.update(tracks, current_timestamp=timestamp))

        motion_steps = {step.object_id: step for step in self._trajectory_manager.update(tracks)}
        speed_samples = {sample.object_id: sample for sample in self._speed_estimator.update(tracks)}

        for track in tracks:
            point = centroid(track.bbox)

            for crossing in self._line_detector.update(track.object_id, point):
                events.append(build_line_crossed_event(track, crossing, self.camera_id))

            for transition in self._zone_detector.update(track.object_id, point, track.timestamp, track.frame_id):
                if transition.transition == "entered":
                    events.append(build_zone_entered_event(track, transition, self.camera_id))
                else:
                    events.append(build_zone_exited_event(track, transition, self.camera_id))

            for zone_id in self._zone_ids:
                is_inside = self._zone_detector.is_inside(track.object_id, zone_id)
                self._dwell_tracker.update(track.object_id, zone_id, is_inside, track.timestamp)
                if is_inside:
                    loitering_event = self._loitering_rule.update(
                        track, zone_id, self._dwell_tracker, track.timestamp
                    )
                    if loitering_event is not None:
                        events.append(loitering_event)

            step = motion_steps.get(track.object_id)
            stopped_event = self._stopped_rule.update(track, step)
            if stopped_event is not None:
                events.append(stopped_event)

            sudden_stop_event = self._sudden_stop_rule.update(track, step)
            if sudden_stop_event is not None:
                events.append(sudden_stop_event)

            sample = speed_samples.get(track.object_id)
            overspeed_event = self._overspeed_rule.update(track, sample)
            if overspeed_event is not None:
                events.append(overspeed_event)

        return events
