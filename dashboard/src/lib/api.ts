/**
 * TRACE API client. Every function here talks to the real Phase 9/10 FastAPI
 * backend -- no mock/hardcoded data. Base URL is configurable via
 * VITE_API_BASE_URL (see .env), defaulting to http://localhost:8000 (plain
 * `uvicorn api.app:app`'s own default port).
 */

const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000'

export interface Camera {
  id: number
  camera_id: string
  name: string | null
  location: string | null
  calibration_reference: string | null
}

export interface Video {
  id: number
  camera_id: number
  path: string
  started_at: string | null
}

export interface TrackedObjectSummary {
  id: number
  object_id: number
  class_name: string
  first_seen: number
  last_seen: number
}

export interface TrackPoint {
  frame_id: number
  timestamp: number
  x: number
  y: number
  x_min: number | null
  y_min: number | null
  x_max: number | null
  y_max: number | null
}

export interface Trajectory {
  object_id: number
  camera_id: string
  class_name: string
  first_seen: number
  last_seen: number
  points: TrackPoint[]
}

export interface TraceEvent {
  id: number
  object_id: number
  event_type: string
  class_name: string
  timestamp: number
  confidence: number
  metadata: Record<string, unknown>
  zone_id: string | null
  line_id: string | null
}

export interface Zone {
  id: number
  zone_id: string
  polygon: [number, number][]
}

export interface Line {
  id: number
  line_id: string
  start: [number, number]
  end: [number, number]
}

export interface AnalyticsSummary {
  camera_id: string | null
  start_time: number | null
  end_time: number | null
  object_count: number
  line_crossing_count: number
  zone_violation_count: number
  average_dwell_time: number
  traffic_volume: number
  event_frequency: Record<string, number>
  per_class_stats: Record<string, { object_count: number; event_count: number }>
}

async function readErrorDetail(response: Response): Promise<string> {
  const body = await response.text()
  try {
    const parsed = JSON.parse(body) as { detail?: string }
    if (typeof parsed.detail === 'string') return parsed.detail
  } catch {
    // not JSON -- fall through to the raw body
  }
  return body
}

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`)
  if (!response.ok) {
    throw new Error(await readErrorDetail(response))
  }
  return response.json() as Promise<T>
}

async function apiPost<T>(path: string, payload: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    throw new Error(await readErrorDetail(response))
  }
  return response.json() as Promise<T>
}

export function listCameras(): Promise<Camera[]> {
  return apiGet<Camera[]>('/cameras')
}

export function listVideos(cameraId?: string): Promise<Video[]> {
  const query = cameraId ? `?camera_id=${encodeURIComponent(cameraId)}` : ''
  return apiGet<Video[]>(`/videos${query}`)
}

export function listCameraObjects(cameraId: string): Promise<TrackedObjectSummary[]> {
  return apiGet<TrackedObjectSummary[]>(`/cameras/${encodeURIComponent(cameraId)}/objects`)
}

export function getObjectTrajectory(objectId: number): Promise<Trajectory> {
  return apiGet<Trajectory>(`/objects/${objectId}/trajectory`)
}

export interface EventFilters {
  eventType?: string
  startTime?: number
  endTime?: number
}

/**
 * GET /cameras/{camera_id}/events already supports event_type/start_time/
 * end_time server-side filtering (src/api/routers/cameras.py) -- Phase 10.3's
 * Event Investigation view filters through this, not client-side, since the
 * backend is the source of truth and can scale past what's fetched in one
 * page.
 */
export function listCameraEvents(cameraId: string, filters: EventFilters = {}): Promise<TraceEvent[]> {
  const params = new URLSearchParams()
  if (filters.eventType) params.set('event_type', filters.eventType)
  if (filters.startTime !== undefined) params.set('start_time', String(filters.startTime))
  if (filters.endTime !== undefined) params.set('end_time', String(filters.endTime))
  const query = params.toString() ? `?${params.toString()}` : ''
  return apiGet<TraceEvent[]>(`/cameras/${encodeURIComponent(cameraId)}/events${query}`)
}

export function listCameraZones(cameraId: string): Promise<Zone[]> {
  return apiGet<Zone[]>(`/cameras/${encodeURIComponent(cameraId)}/zones`)
}

export function listCameraLines(cameraId: string): Promise<Line[]> {
  return apiGet<Line[]>(`/cameras/${encodeURIComponent(cameraId)}/lines`)
}

export function getVideoStreamUrl(videoId: number): string {
  return `${API_BASE_URL}/videos/${videoId}/stream`
}

/**
 * GET /analytics bundles 7 of Section 11's 8 analytics functions for one
 * camera/time-range filter; `busiest_hours` isn't in that bundle (see
 * TRACE_STUDY_GUIDE.md Section 19), so the dashboard computes it itself from
 * `listCameraEvents`'s raw events -- see src/lib/analytics.ts.
 */
export function getAnalytics(cameraId?: string): Promise<AnalyticsSummary> {
  const query = cameraId ? `?camera_id=${encodeURIComponent(cameraId)}` : ''
  return apiGet<AnalyticsSummary>(`/analytics${query}`)
}

export interface AlertRecord {
  id: number
  camera_id: string
  event_id: number | null
  event_type: string
  message: string
  channel: string
  created_at: string
}

/**
 * GET /cameras/{camera_id}/alerts -- Section 13's dashboard/API delivery
 * channel: an alert is "delivered" by existing here, queryable. These are
 * real Alert rows created automatically (src/database/repository.py's
 * should_alert) when a qualifying event is ingested for this camera --
 * currently just OVERSPEED (src/alerts/rules.py's ALERT_TRIGGERING_EVENT_TYPES;
 * ZONE_ENTERED/SUDDEN_STOP/LINE_CROSSED are not wired to alerting yet).
 */
export function listCameraAlerts(cameraId: string): Promise<AlertRecord[]> {
  return apiGet<AlertRecord[]>(`/cameras/${encodeURIComponent(cameraId)}/alerts`)
}

export interface AgentToolCall {
  name: string
  arguments: Record<string, unknown>
  result: Record<string, unknown>
}

export interface AgentAnswer {
  answer: string
  tool_calls: AgentToolCall[]
}

/**
 * POST /agent/query -- Section 12's Vision Agent. Grounded: every answer is
 * backed by real tool calls over the same repository/analytics layer the
 * rest of the dashboard reads (src/agent/tools.py), returned alongside the
 * answer for transparency. Returns a 503 with a clear detail message if no
 * LLM API key is configured in this environment (src/api/deps.py) -- that's
 * a real, honest state to surface, not an error to hide.
 */
export function queryAgent(question: string): Promise<AgentAnswer> {
  return apiPost<AgentAnswer>('/agent/query', { question })
}

/**
 * GET /evaluation -- Phase 17's Model Evaluation view. Types below mirror
 * the real, checked-in Phase 14 evaluation-harness output
 * (evaluation/results/detection_comparison.json,
 * evaluation/results/tracking_comparison.json) field-for-field; the backend
 * route is a near-verbatim passthrough of those files (see
 * src/api/routers/evaluation.py), so there is exactly one place these
 * numbers are ever written down -- not duplicated here.
 */
export interface DetectionClassMetric {
  Class: string
  Images: number
  Instances: number
  'Box-P': number
  'Box-R': number
  'Box-F1': number
  mAP50: number
  'mAP50-95': number
  model: string
}

export interface DetectionHoldout {
  weights: Record<string, string>
  per_class: Record<string, Record<string, DetectionClassMetric>>
}

export interface DetectionComparison {
  coco_holdout: DetectionHoldout
  real_footage_holdout: DetectionHoldout
}

export interface TrackingResult {
  mota: number
  idf1: number
  num_switches: number
  num_false_positives: number
  num_misses: number
  num_matches: number
}

export interface TrackingComparison {
  real_footage: {
    ground_truth_frames: number
    weights: Record<string, string>
    results: Record<string, TrackingResult>
  }
  synthetic_crossing: {
    ground_truth_frames: number
    results: TrackingResult
  }
}

export interface EvaluationData {
  detection: DetectionComparison
  tracking: TrackingComparison
}

export function getEvaluation(): Promise<EvaluationData> {
  return apiGet<EvaluationData>('/evaluation')
}
