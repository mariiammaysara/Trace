import { useState, useEffect } from 'react'
import { Sidebar, type ActiveView } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { DashboardView } from '@/components/DashboardView'
import { LiveView } from '@/components/LiveView'
import { EventsView } from '@/components/EventsView'
import { AnalyticsView } from '@/components/AnalyticsView'
import { listCameras, type Camera } from '@/lib/api'
import { Card, CardContent } from '@/components/ui/card'
import { ShieldAlert, Bot } from 'lucide-react'

const VIEW_METADATA: Record<ActiveView, { title: string; subtitle: string }> = {
  dashboard: {
    title: 'Dashboard',
    subtitle: 'Real-time overview of your video intelligence system',
  },
  cameras: {
    title: 'Cameras',
    subtitle: 'Live fleet and sensor stream management',
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
    title: 'Investigations',
    subtitle: 'Deep-dive video telemetry and incident reconstruction',
  },
  alerts: {
    title: 'Alerts',
    subtitle: 'Automated violation alarms and rule configuration',
  },
  agent: {
    title: 'Vision Agent',
    subtitle: 'AI assistant for multimodal video queries',
  },
}

function App() {
  const [activeView, setActiveView] = useState<ActiveView>('dashboard')
  const [cameras, setCameras] = useState<Camera[]>([])
  const [selectedCameraId, setSelectedCameraId] = useState<string | null>(null)
  const [isApiConnected, setIsApiConnected] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

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

  const currentMeta = VIEW_METADATA[activeView] ?? VIEW_METADATA.dashboard

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground antialiased">
      {/* Desktop & Mobile Sidebar */}
      <div className="hidden md:flex">
        <Sidebar
          activeView={activeView}
          onNavigate={(view) => setActiveView(view)}
          cameraCount={cameras.length}
          isApiConnected={isApiConnected}
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
            />
          </div>
        </div>
      )}

      {/* Main Application Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header
          title={currentMeta.title}
          subtitle={currentMeta.subtitle}
          cameras={cameras}
          selectedCameraId={selectedCameraId}
          onSelectCamera={(id) => setSelectedCameraId(id)}
          onToggleMobileMenu={() => setMobileMenuOpen(!mobileMenuOpen)}
          onRefresh={fetchCameras}
          isRefreshing={isRefreshing}
        />

        <main className="flex-1 overflow-y-auto p-4 md:p-6">
          {activeView === 'dashboard' && (
            <DashboardView
              onNavigateToEvents={() => setActiveView('events')}
              onNavigateToAnalytics={() => setActiveView('analytics')}
            />
          )}

          {activeView === 'cameras' && <LiveView />}
          {activeView === 'events' && <EventsView />}
          {activeView === 'investigations' && <EventsView />}
          {activeView === 'analytics' && <AnalyticsView />}

          {activeView === 'alerts' && (
            <Card className="max-w-2xl mx-auto border-border bg-surface p-8 text-center mt-8 shadow-xs">
              <CardContent className="flex flex-col items-center justify-center p-0">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-danger/10 text-danger mb-3">
                  <ShieldAlert className="h-6 w-6" />
                </div>
                <h2 className="text-base font-semibold text-primary">Alert Dispatch System</h2>
                <p className="text-xs text-secondary mt-1 max-w-md">
                  Active alert webhooks are configured on the FastAPI backend for real-time violation notifications (Overspeed, Zone Intrusion, Sudden Stop).
                </p>
              </CardContent>
            </Card>
          )}

          {activeView === 'agent' && (
            <Card className="max-w-2xl mx-auto border-border bg-surface p-8 text-center mt-8 shadow-xs">
              <CardContent className="flex flex-col items-center justify-center p-0">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-accent/20 text-secondary mb-3">
                  <Bot className="h-6 w-6" />
                </div>
                <h2 className="text-base font-semibold text-primary">Vision Intelligence Agent</h2>
                <p className="text-xs text-secondary mt-1 max-w-md">
                  Natural language video query and scene description agent powered by TRACE tracking and trajectory telemetry.
                </p>
              </CardContent>
            </Card>
          )}
        </main>
      </div>
    </div>
  )
}

export default App
