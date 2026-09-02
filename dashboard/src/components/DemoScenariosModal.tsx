import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { EventBadge } from '@/components/EventBadge'
import { DEMO_SCENARIOS, type DemoScenario } from '@/lib/demoScenarios'
import { cn } from '@/lib/utils'
import { Sparkles, Play, X, ShieldAlert, Route, Eye, Info } from 'lucide-react'

interface DemoScenariosModalProps {
  isOpen: boolean
  onClose: () => void
  onLaunchScenario: (scenario: DemoScenario) => void
  activeScenarioId?: string | null
}

const CATEGORY_ICONS = {
  Security: ShieldAlert,
  'Access Control': Route,
  Tracking: Eye,
}

export function DemoScenariosModal({
  isOpen,
  onClose,
  onLaunchScenario,
  activeScenarioId,
}: DemoScenariosModalProps) {
  if (!isOpen) return null

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="demo-scenarios-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-primary/70 backdrop-blur-xs p-4 animate-in fade-in-0 duration-150"
    >
      <div className="relative flex max-h-[90vh] w-full max-w-3xl flex-col rounded-xl border border-border bg-surface shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-5 py-4 bg-surface-alt/40">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent/15 text-secondary">
              <Sparkles className="h-4 w-4" />
            </div>
            <div>
              <h2 id="demo-scenarios-title" className="text-base font-semibold text-ink leading-tight">
                Demo Scenarios
              </h2>
              <p className="text-xs text-ink-subtle">
                Pre-recorded pipeline walkthroughs powered by real computer vision data
              </p>
            </div>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            onClick={onClose}
            aria-label="Close demo scenarios dialog"
            className="text-ink-subtle hover:text-ink"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Content list */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          <div className="grid grid-cols-1 gap-3.5">
            {DEMO_SCENARIOS.map((scenario) => {
              const Icon = CATEGORY_ICONS[scenario.category] ?? Sparkles
              const isActive = activeScenarioId === scenario.id

              return (
                <Card
                  key={scenario.id}
                  className={cn(
                    'transition-all duration-150 border',
                    isActive
                      ? 'border-accent bg-accent/5 ring-1 ring-accent'
                      : 'border-border hover:border-secondary/50 bg-surface',
                  )}
                >
                  <CardHeader className="p-4 pb-2">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <div className="flex h-6 w-6 items-center justify-center rounded bg-surface-alt text-ink-subtle">
                          <Icon className="h-3.5 w-3.5" />
                        </div>
                        <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-quiet">
                          {scenario.category}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <EventBadge eventType={scenario.targetEventType} />
                      </div>
                    </div>
                    <CardTitle className="text-sm font-semibold text-ink mt-1.5">
                      {scenario.title}
                    </CardTitle>
                  </CardHeader>

                  <CardContent className="p-4 pt-1 space-y-3">
                    <p className="text-xs text-ink-subtle leading-relaxed">
                      {scenario.description}
                    </p>

                    <div className="rounded-md bg-surface-alt/60 p-2.5 text-[11px] text-ink-quiet border border-border/50">
                      <span className="font-semibold text-ink mr-1">Pipeline Validation:</span>
                      {scenario.keyLearnings}
                    </div>

                    <div className="flex items-center justify-between pt-1">
                      <div className="flex items-center gap-3 text-[11px] font-mono text-ink-quiet">
                        <span>Feed: <strong className="text-ink">{scenario.cameraId}</strong></span>
                        <span>•</span>
                        <span>Source: <strong className="text-ink">{scenario.videoName}</strong></span>
                      </div>

                      <Button
                        type="button"
                        size="sm"
                        onClick={() => {
                          onLaunchScenario(scenario)
                          onClose()
                        }}
                        className={cn(
                          'gap-1.5 text-xs font-semibold px-3 h-8 shadow-xs',
                          isActive
                            ? 'bg-secondary text-ink-on-dark'
                            : 'bg-primary hover:bg-primary/90 text-ink-on-dark',
                        )}
                      >
                        <Play className="h-3 w-3 fill-current" />
                        {isActive ? 'Replay Scenario' : 'Launch Scenario'}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>

          {/* Honest footprint disclosure */}
          <div className="flex items-start gap-2 rounded-lg border border-border/70 bg-surface-alt/40 p-3 text-xs text-ink-subtle">
            <Info className="h-4 w-4 text-ink-subtle shrink-0 mt-0.5" />
            <p>
              <strong>Footprint transparency:</strong> Scenarios are constrained to real footage (<code className="font-mono text-[11px]">data/sample.mp4</code>) and deterministic event rules currently in the repository. Scenarios requiring high-speed vehicles (<code className="font-mono text-[11px]">OVERSPEED</code>) are omitted until vehicular footage is added.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end border-t border-border px-5 py-3 bg-surface-alt/20">
          <Button type="button" variant="outline" size="sm" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </div>
  )
}
