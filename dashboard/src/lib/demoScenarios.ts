/**
 * TRACE Demo Scenarios (Phase 20).
 *
 * Provides a structured way to demonstrate the full TRACE video intelligence
 * pipeline (Detection -> Tracking -> Geometry -> Event Engine -> Investigation)
 * without requiring live physical RTSP cameras or waiting for random events.
 *
 * HONEST FOOTPRINT RULE:
 * Every scenario here maps strictly to real footage and real events produced
 * by our event engine on the named camera. We deliberately DO NOT offer an
 * OVERSPEED scenario on any camera below because none of them have a real,
 * surveyed camera calibration -- see configs/cameras/*.json's own comments.
 * Fabricating synthetic scenarios without real footage is prohibited.
 *
 * Phase 20 update: two stock videos of the original three considered for
 * this phase ("Busy intersection aerial view", "Vehicular movement... at a
 * junction") were evaluated and found unusable for a detection/tracking
 * scenario -- TRACE's pretrained YOLOv8n detector has a real, measured
 * domain gap on straight-down/nadir drone footage (avg. 0.01-0.03
 * detections/frame at the default 0.25 confidence threshold, vs. 16.1/frame
 * on street-level footage of comparable density -- see
 * TRACE_STUDY_GUIDE.md Section 17). They are used for benchmarking only
 * (benchmarks/results/), not as an interactive scenario here, since there
 * is nothing real for a click-through demo to show.
 */

export interface DemoScenario {
  id: string
  title: string
  category: 'Security' | 'Access Control' | 'Tracking'
  description: string
  cameraId: string
  videoName: string
  targetEventType: string
  startTime: number
  keyLearnings: string
  severity: 'danger' | 'warning' | 'info'
}

export const DEMO_SCENARIOS: DemoScenario[] = [
  {
    id: 'zone-intrusion',
    title: 'Restricted Area Perimeter Intrusion',
    category: 'Security',
    description:
      'A tracked person walks into the calibrated restricted zone polygon, triggering a deterministic ZONE_ENTERED violation event.',
    cameraId: 'demo',
    videoName: 'sample.mp4',
    targetEventType: 'ZONE_ENTERED',
    startTime: 0.0,
    keyLearnings:
      'Demonstrates Point-in-Polygon geometric intersection, debounce hysteresis to prevent edge flicker, and real-time danger-state overlay rendering.',
    severity: 'danger',
  },
  {
    id: 'line-crossing',
    title: 'Perimeter Tripwire Line Crossing',
    category: 'Access Control',
    description:
      'A pedestrian crosses the calibrated entrance boundary line, triggering a LINE_CROSSED event with directional vector classification (A -> B).',
    cameraId: 'demo',
    videoName: 'sample.mp4',
    targetEventType: 'LINE_CROSSED',
    startTime: 1.0,
    keyLearnings:
      'Demonstrates continuous segment-intersection vector math between consecutive trajectory points and a virtual line segment.',
    severity: 'warning',
  },
  {
    id: 'track-lifecycle',
    title: 'Object Localization & Persistent Tracking',
    category: 'Tracking',
    description:
      'Object detection establishes a persistent Kalman-filtered track with stable object_id that survives frame-to-frame motion.',
    cameraId: 'demo',
    videoName: 'sample.mp4',
    targetEventType: 'OBJECT_APPEARED',
    startTime: 0.0,
    keyLearnings:
      'Demonstrates YOLOv8 detection bounding boxes, ByteTrack two-stage Hungarian association, and ground-plane trajectory accumulation.',
    severity: 'info',
  },
  {
    id: 'trafficlight-line-crossing',
    title: 'Street Intersection Vehicle Line Crossing',
    category: 'Access Control',
    description:
      'Real stock footage of a static street-corner traffic light. A tracked vehicle (object_id=2) crosses a calibrated tripwire line placed across the crosswalk, triggering a real LINE_CROSSED event -- verified by actually running the pipeline, not assumed.',
    cameraId: 'demo-trafficlight',
    videoName: 'demo_trafficlight.mp4',
    targetEventType: 'LINE_CROSSED',
    startTime: 8.5,
    keyLearnings:
      'Demonstrates the same pixel-space line-segment intersection geometry as the "demo" camera scenario above, this time against real (non-synthetic) street footage with a static camera. This camera has only an illustrative/placeholder homography (no real-world survey exists for this stock footage), so no speed or OVERSPEED claim is made here -- only LINE_CROSSED, which is pure pixel-space geometry and does not depend on the homography scale.',
    severity: 'warning',
  },
]
