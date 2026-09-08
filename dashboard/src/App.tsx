import { useState, useEffect } from 'react'
import { Sidebar, type ActiveView } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { DashboardView } from '@/components/DashboardView'
import { LiveView } from '@/components/LiveView'
import { CamerasView } from '@/components/CamerasView'
import { EventsView } from '@/components/EventsView'
import { AnalyticsView } from '@/components/AnalyticsView'
import { AlertsView } from '@/components/AlertsView'
import { VisionAgentView } from '@/components/VisionAgentView'
import { EvaluationView } from '@/components/EvaluationView'
import { ObjectProfilePanel } from '@/components/ObjectProfilePanel'
import { DemoScenariosModal } from '@/components/DemoScenariosModal'
import { type UploadEntry } from '@/components/RecentUploadsPanel'
import { type DemoScenario } from '@/lib/demoScenarios'
import { type SeekRequest } from '@/components/VideoPlayer'
import { listCameras, type Camera, type Video } from '@/lib/api'
import { useCameraScene } from '@/hooks/useCameraScene'
import { classifyEventSeverity } from '@/lib/eventSeverity'
import type { AgentEventRef } from '@/lib/agentInsights'

const RECENT_UPLOADS_STORAGE_KEY = 'trace.recentUploads'

function loadStoredUploads(): UploadEntry[] {
  try {
    const raw = localStorage.getItem(RECENT_UPLOADS_STORAGE_KEY)
    return raw ? (JSON.parse(raw) as UploadEntry[]) : []
  } catch {
    return []
  }
}

const VIEW_METADATA: Record<ActiveView, { title: string; subtitle: string }> = {
  dashboard: {
    title: 'Overview',
    subtitle: 'Real-time overview of your video intelligence system',
  },
  live: {
    title: 'Live',
    subtitle: 'Real-time monitoring with detection and tracking overlays',
  },
  cameras: {
    title: 'Cameras',
    subtitle: 'Fleet status and sensor management',
  },
  events: {
    title: 'Events',
    subtitle: 'Incident logging and forensic search',
  },
  analytics: {
    title: 'Analytics',
    subtitle: 'Statistical breakdowns and spatial metrics',
  },
  investigations: {
    title: 'Investigation',
    subtitle: 'Deep-dive video telemetry and incident reconstruction',
  },
  alerts: {
    title: 'Alerts',
    subtitle: 'Dispatched violation alerts across the fleet',
  },
  agent: {
    title: 'Vision Agent',
    subtitle: 'Ask questions grounded in real TRACE tracking data',
  },
  evaluation: {
    title: 'Evaluation',
    subtitle: 'Real fine-tuning results: baseline vs. Stage 1 vs. Stage 2',
  },
}

function App() {
  const [activeView, setActiveView] = useState<ActiveView>('dashboard')
  const [cameras, setCameras] = useState<Camera[]>([])
  const [selectedCameraId, setSelectedCameraId] = useState<string | null>(null)
  const [isApiConnected, setIsApiConnected] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  // Phase 19: Object Profile Panel
  const [openObjectId, setOpenObjectId] = useState<number | null>(null)
  const [pendingInvestigationEventId, setPendingInvestigationEventId] = useState<number | null>(null)

  // Phase 20: Demo Scenarios & In-Demo Event Notification Stream
  const [isDemoModalOpen, setIsDemoModalOpen] = useState(false)
  const [activeScenario, setActiveScenario] = useState<DemoScenario | null>(null)
  const [demoSeekRequest, setDemoSeekRequest] = useState<SeekRequest | null>(null)

  // Video upload feature: lifted above CamerasView (not local to it) and
  // mirrored to localStorage so a real in-progress upload isn't lost either
  // by switching tabs (CamerasView unmounts) or by a full page reload --
  // each row still polls its own real status independently (RecentUploadsPanel).
  const [uploads, setUploads] = useState<UploadEntry[]>(() => loadStoredUploads())

  useEffect(() => {
    try {
      localStorage.setItem(RECENT_UPLOADS_STORAGE_KEY, JSON.stringify(uploads))
    } catch {
      // best-effort persistence only -- a full/unavailable localStorage
      // shouldn't break the upload feature itself
    }
  }, [uploads])

  function handleVideoUploaded(video: Video, cameraId: string, filename: string) {
    setUploads((current) => [...current, { videoId: video.id, cameraId, filename, createdAt: Date.now() }])
    fetchCameras()
  }

  function handleCameraDeleted(cameraId: string) {
    // Drop any Recent Uploads entries pointing at the now-deleted camera --
    // their video row is gone too (cascaded server-side), so polling their
    // status would just 404 forever.
    setUploads((current) => current.filter((upload) => upload.cameraId !== cameraId))
    // Clear the selection if it was the deleted camera -- whatever view is
    // currently showing it (Live, Analytics, Investigation) reads
    // selectedCameraId as a prop, so this is the real "redirect away":
    // fetchCameras() below picks a fresh default once the updated camera
    // list comes back, same as on initial load.
    setSelectedCameraId((current) => (current === cameraId ? null : current))
    fetchCameras()
  }

  const fetchCameras = () => {
    setIsRefreshing(true)
    listCameras()
      .then((result) => {
        setCameras(result)
        setIsApiConnected(true)
        setSelectedCameraId((current) => current ?? result[0]?.camera_id ?? null)
      })
      .catch(() => {
        setIsApiConnected(false)
      })
      .finally(() => {
        setIsRefreshing(false)
      })
  }

  useEffect(() => {
    fetchCameras()
  }, [])

  function handleLaunchScenario(scenario: DemoScenario) {
    setSelectedCameraId(scenario.cameraId)
    setActiveScenario(scenario)
    setActiveView('live')
    setDemoSeekRequest({ time: scenario.startTime, nonce: Date.now() })
  }

  function handleInvestigateEvent(eventId: number) {
    setPendingInvestigationEventId(eventId)
    setActiveView('investigations')
  }

  const currentMeta = VIEW_METADATA[activeView] ?? VIEW_METADATA.dashboard

  // The header's Operations Telemetry Strip reflects whatever camera is
  // currently selected, regardless of which page is open -- fetched once
  // here rather than reading it out of Dashboard/LiveView's own internal
  // useCameraScene calls (those stay page-local; this is a separate fetch
  // for the persistent header, same real data, one extra request per camera
  // switch in exchange for not threading page-owned state up through props).
  const headerScene = useCameraScene(selectedCameraId)
  const criticalEvents = headerScene.events.filter((event) => classifyEventSeverity(event.event_type) === 'danger')
  const criticalEvent = criticalEvents[criticalEvents.length - 1] ?? null

  function handleSeekToCriticalEvent(timestamp: number) {
    setActiveView('live')
    setDemoSeekRequest({ time: timestamp, nonce: Date.now() })
  }

  // Vision Agent answers can reference events on ANY camera (its tools
  // aren't scoped to whatever's currently selected in the UI), so replaying
  // one also switches the selected camera before seeking -- unlike the
  // header's critical-breach chip, which is always about the already-active
  // camera.
  function handleReplayAgentEvent(ref: AgentEventRef) {
    setSelectedCameraId(ref.camera_id)
    setActiveView('live')
    setDemoSeekRequest({ time: ref.timestamp, nonce: Date.now() })
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground antialiased">
      {/* Desktop & Mobile Sidebar */}
      <div className="hidden md:flex">
        <Sidebar
          activeView={activeView}
          onNavigate={(view) => setActiveView(view)}
          cameraCount={cameras.length}
          isApiConnected={isApiConnected}
          criticalEventCount={criticalEvents.length}
        />
      </div>

      {/* Mobile Drawer Overlay */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden">
          <div
            className="fixed inset-0 bg-primary/60 backdrop-blur-xs"
            onClick={() => setMobileMenuOpen(false)}
          />
          <div className="relative z-10 flex h-full">
            <Sidebar
              activeView={activeView}
              onNavigate={(view) => {
                setActiveView(view)
                setMobileMenuOpen(false)
              }}
              cameraCount={cameras.length}
              isApiConnected={isApiConnected}
              criticalEventCount={criticalEvents.length}
            />
          </div>
        </div>
      )}

      {/* Main Application Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header
          title={currentMeta.title}
          cameras={cameras}
          selectedCameraId={selectedCameraId}
          onSelectCamera={(id) => setSelectedCameraId(id)}
          onToggleMobileMenu={() => setMobileMenuOpen(!mobileMenuOpen)}
          onRefresh={fetchCameras}
          isRefreshing={isRefreshing}
          onOpenDemoModal={() => setIsDemoModalOpen(true)}
          isApiConnected={isApiConnected}
          targetsInFrame={selectedCameraId ? headerScene.trajectories.length : undefined}
          criticalEventCount={criticalEvents.length}
          onSeekToCriticalEvent={
            criticalEvent ? () => handleSeekToCriticalEvent(criticalEvent.timestamp) : undefined
          }
        />

        <main className="flex-1 overflow-y-auto p-4 md:p-6">
          {activeView === 'dashboard' && (
            <DashboardView
              cameras={cameras}
              selectedCameraId={selectedCameraId}
              onSelectCamera={setSelectedCameraId}
              onNavigateToEvents={() => setActiveView('events')}
              onNavigateToAnalytics={() => setActiveView('analytics')}
            />
          )}

          {activeView === 'live' && (
            <LiveView
              cameras={cameras}
              selectedCameraId={selectedCameraId}
              onSelectCamera={setSelectedCameraId}
              onSelectObject={setOpenObjectId}
              externalSeekRequest={demoSeekRequest}
              onInvestigateEvent={handleInvestigateEvent}
              activeScenarioTitle={activeScenario?.title}
              onOpenDemoModal={() => setIsDemoModalOpen(true)}
            />
          )}
          {activeView === 'cameras' && (
            <CamerasView
              cameras={cameras}
              selectedCameraId={selectedCameraId}
              onSelectCamera={setSelectedCameraId}
              onNavigateToLive={() => setActiveView('live')}
              uploads={uploads}
              onVideoUploaded={handleVideoUploaded}
              onCameraDeleted={handleCameraDeleted}
            />
          )}
          {activeView === 'events' && (
            <EventsView
              cameras={cameras}
              selectedCameraId={selectedCameraId}
              onSelectCamera={setSelectedCameraId}
              mode="events"
              onSelectObject={setOpenObjectId}
            />
          )}
          {activeView === 'investigations' && (
            <EventsView
              cameras={cameras}
              selectedCameraId={selectedCameraId}
              onSelectCamera={setSelectedCameraId}
              mode="investigation"
              onSelectObject={setOpenObjectId}
              initialEventId={pendingInvestigationEventId}
              onInitialEventConsumed={() => setPendingInvestigationEventId(null)}
            />
          )}
          {activeView === 'analytics' && (
            <AnalyticsView
              cameras={cameras}
              selectedCameraId={selectedCameraId}
              onSelectCamera={setSelectedCameraId}
            />
          )}
          {activeView === 'alerts' && <AlertsView cameras={cameras} />}
          {activeView === 'agent' && <VisionAgentView onReplayEvent={handleReplayAgentEvent} />}
          {activeView === 'evaluation' && <EvaluationView />}
        </main>
      </div>

      {/* Global Object Profile Panel (Phase 19) */}
      <ObjectProfilePanel
        objectId={openObjectId}
        onClose={() => setOpenObjectId(null)}
        onOpenIncident={(eventId) => {
          setOpenObjectId(null)
          setPendingInvestigationEventId(eventId)
          setActiveView('investigations')
        }}
      />

      {/* Global Demo Scenarios Modal (Phase 20) */}
      <DemoScenariosModal
        isOpen={isDemoModalOpen}
        onClose={() => setIsDemoModalOpen(false)}
        onLaunchScenario={handleLaunchScenario}
        activeScenarioId={activeScenario?.id}
      />
    </div>
  )
}

export default App
