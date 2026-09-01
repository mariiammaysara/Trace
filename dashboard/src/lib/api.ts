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

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`)
  if (!response.ok) {
    const body = await response.text()
    throw new Error(`GET ${path} failed: ${response.status} ${body}`)
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

export function listCameraEvents(cameraId: string): Promise<TraceEvent[]> {
  return apiGet<TraceEvent[]>(`/cameras/${encodeURIComponent(cameraId)}/events`)
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
