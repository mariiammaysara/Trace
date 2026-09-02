/**
 * TRACE Demo Scenarios (Phase 20).
 *
 * Provides a structured way to demonstrate the full TRACE video intelligence
 * pipeline (Detection -> Tracking -> Geometry -> Event Engine -> Investigation)
 * without requiring live physical RTSP cameras or waiting for random events.
 *
 * HONEST FOOTPRINT RULE:
 * Every scenario here maps strictly to REAL footage (data/sample.mp4) and REAL
 * events produced by our event engine on camera 'demo'. We deliberately DO NOT
 * offer an OVERSPEED scenario because sample.mp4 contains a pedestrian walking,
 * not a speeding vehicle. Fabricating synthetic scenarios without real footage
 * is prohibited.
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
]
