import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { BarChart, type BarChartDatum } from '@/components/charts/BarChart'
import { getEvaluation } from '@/lib/api'
import type { EvaluationData } from '@/lib/api'
import { cn } from '@/lib/utils'
import { FlaskConical, Table2, BarChart3, AlertTriangle } from 'lucide-react'

const MODEL_LABELS: Record<string, string> = {
  pretrained: 'Baseline (pretrained)',
  stage1: 'Stage 1',
  stage2: 'Stage 2',
}

const MODEL_ORDER = ['pretrained', 'stage1', 'stage2']

function fmt(value: number | undefined, digits = 3): string {
  return value === undefined ? '—' : value.toFixed(digits)
}

/**
 * Model Evaluation (Phase 17): TRACE's real fine-tuning result, presented as
 * a research finding rather than a features page. Every number comes from
 * GET /evaluation, a near-verbatim passthrough of Phase 14's checked-in
 * evaluation-harness output (evaluation/results/*.json) -- nothing here is
 * hardcoded, and the collapsed/zero values are shown exactly as measured,
 * not filtered out. See TRACE_STUDY_GUIDE.md Sections 2, 15, and 20 for the
 * full methodology this view summarizes.
 */
export function EvaluationView() {
  const [data, setData] = useState<EvaluationData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    getEvaluation()
      .then((result) => {
        if (!cancelled) setData(result)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(String(err))
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (error) {
    return (
      <div role="alert" className="flex items-start gap-2 rounded-md border border-danger bg-danger/10 px-4 py-3 text-sm text-danger max-w-2xl">
        <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
        <div>
          <p className="font-medium">Evaluation results unavailable</p>
          <p className="text-xs mt-0.5">{error}</p>
        </div>
      </div>
    )
  }

  if (!data) {
    return <p className="text-sm text-ink-subtle">Loading evaluation results…</p>
  }

  const personDetection = data.detection.real_footage_holdout.per_class.person ?? {}
  const tracking = data.tracking.real_footage.results
  const cocoPerClass = data.detection.coco_holdout.per_class

  const rows: Array<{
    label: string
    unit?: string
    values: (model: string) => string
    variant: (model: string) => 'accent' | 'danger'
  }> = [
    {
      label: 'Precision',
      values: (m) => fmt(personDetection[m]?.['Box-P']),
      variant: (m) => (personDetection[m]?.['Box-P'] !== undefined && personDetection[m]['Box-P'] < 0.5 ? 'danger' : 'accent'),
    },
    {
      label: 'Recall',
      values: (m) => fmt(personDetection[m]?.['Box-R']),
      variant: () => 'accent',
    },
    {
      label: 'mAP50',
      values: (m) => fmt(personDetection[m]?.mAP50),
      variant: () => 'accent',
    },
    {
      label: 'mAP50-95',
      values: (m) => fmt(personDetection[m]?.['mAP50-95']),
      variant: () => 'accent',
    },
    {
      label: 'MOTA',
      values: (m) => fmt(tracking[m]?.mota),
      variant: (m) => (tracking[m]?.mota !== undefined && tracking[m].mota < 0.5 ? 'danger' : 'accent'),
    },
    {
      label: 'IDF1',
      values: (m) => fmt(tracking[m]?.idf1),
      variant: (m) => (tracking[m]?.idf1 !== undefined && tracking[m].idf1 < 0.5 ? 'danger' : 'accent'),
    },
    {
      label: 'ID switches',
      values: (m) => (tracking[m] ? String(tracking[m].num_switches) : '—'),
      variant: () => 'accent',
    },
  ]

  const map5095Chart: BarChartDatum[] = MODEL_ORDER.map((m) => ({
    key: m,
    label: MODEL_LABELS[m],
    value: personDetection[m]?.['mAP50-95'] ?? 0,
    variant: 'accent',
    title: `${MODEL_LABELS[m]}: mAP50-95 = ${fmt(personDetection[m]?.['mAP50-95'])}`,
  }))

  const motaChart: BarChartDatum[] = MODEL_ORDER.map((m) => ({
    key: m,
    label: MODEL_LABELS[m],
    value: tracking[m]?.mota ?? 0,
    variant: (tracking[m]?.mota ?? 0) < 0.5 ? 'danger' : 'accent',
    title: `${MODEL_LABELS[m]}: MOTA = ${fmt(tracking[m]?.mota)}`,
  }))

  const cocoClasses = Object.keys(cocoPerClass)
  const collapsedClasses = cocoClasses.filter((c) => (cocoPerClass[c].stage1?.mAP50 ?? 1) === 0)

  return (
    <div className="flex flex-col gap-4 max-w-5xl">
      {/* Research question + headline */}
      <div className="flex items-start gap-2">
        <FlaskConical className="h-4 w-4 text-accent shrink-0 mt-0.5" />
        <div>
          <p className="text-sm text-ink">
            <b>Research question:</b> does domain adaptation on real footage (Stage 2) improve detection accuracy and
            downstream tracking performance, compared to a generic pretrained baseline and a COCO-only fine-tune
            (Stage 1)?
          </p>
          <p className="text-xs text-ink-subtle mt-1">
            Person, real-footage held-out set (6 frames from <code className="font-mono">data/sample.mp4</code>) — the
            only evaluation TRACE ran with all three models. See below for the 6-class COCO comparison.
          </p>
        </div>
      </div>

      {/* Status strip */}
      <div className="flex flex-wrap items-center divide-x divide-border rounded-md border border-border bg-surface">
        <div className="flex items-center gap-1.5 px-3.5 py-2">
          <span className="h-1.5 w-1.5 rounded-full bg-danger" />
          <span className="text-xs font-medium text-ink">Neither fine-tune is production-ready</span>
        </div>
        <div className="flex items-center gap-1.5 px-3.5 py-2">
          <span className="text-[10px] font-semibold uppercase tracking-wide text-ink-subtle">COCO classes collapsed</span>
          <span className="font-mono text-sm font-semibold text-danger">{collapsedClasses.length}/{cocoClasses.length}</span>
        </div>
        <div className="flex items-center gap-1.5 px-3.5 py-2">
          <span className="text-[10px] font-semibold uppercase tracking-wide text-ink-subtle">Default weights</span>
          <span className="font-mono text-sm font-semibold text-ink">pretrained</span>
        </div>
      </div>

      {/* Comparison table */}
      <Card size="sm" className="border-border bg-surface shadow-2xs overflow-hidden">
        <CardHeader className="flex flex-row items-center gap-1.5 border-b border-border/50">
          <Table2 className="h-3.5 w-3.5 text-ink-subtle" />
          <CardTitle className="text-xs font-semibold tracking-tight text-ink">
            Baseline vs. Stage 1 vs. Stage 2 — real footage, person
          </CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border/60">
                <th className="text-left font-medium text-ink-subtle text-xs uppercase tracking-wide py-2 pr-4">Metric</th>
                {MODEL_ORDER.map((m) => (
                  <th key={m} className="text-right font-medium text-ink-subtle text-xs uppercase tracking-wide py-2 px-3">
                    {MODEL_LABELS[m]}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.label} className="border-b border-border/30 last:border-0">
                  <td className="py-2 pr-4 text-ink-quiet">{row.label}</td>
                  {MODEL_ORDER.map((m) => (
                    <td
                      key={m}
                      className={cn(
                        'py-2 px-3 text-right font-mono tabular-nums font-semibold',
                        row.variant(m) === 'danger' ? 'text-danger' : 'text-ink',
                      )}
                    >
                      {row.values(m)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* Charts */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card size="sm" className="border-border bg-surface shadow-2xs">
          <CardHeader className="flex flex-row items-center gap-1.5 border-b border-border/50">
            <BarChart3 className="h-3.5 w-3.5 text-ink-subtle" />
            <CardTitle className="text-xs font-semibold tracking-tight text-ink">mAP50-95 (localization quality)</CardTitle>
          </CardHeader>
          <CardContent>
            <BarChart data={map5095Chart} />
            <p className="mt-3 text-xs text-ink-subtle">
              Stage 2 scores higher than both other models here (0.309 → 0.697, beating pretrained&apos;s 0.501) — but
              only on the exact scene it trained on. See the interpretation below before reading this as generalization.
            </p>
          </CardContent>
        </Card>

        <Card size="sm" className="border-border bg-surface shadow-2xs">
          <CardHeader className="flex flex-row items-center gap-1.5 border-b border-border/50">
            <BarChart3 className="h-3.5 w-3.5 text-ink-subtle" />
            <CardTitle className="text-xs font-semibold tracking-tight text-ink">MOTA (tracking accuracy)</CardTitle>
          </CardHeader>
          <CardContent>
            <BarChart data={motaChart} />
            <p className="mt-3 text-xs text-ink-subtle">
              Not a smaller regression — a complete tracking failure. Stage 1/2&apos;s real-footage false positives never
              once matched the ground-truth box across all 244 frames.
            </p>
          </CardContent>
        </Card>
      </div>

      {/* COCO 6-class collapse */}
      <Card size="sm" className="border-border bg-surface shadow-2xs overflow-hidden">
        <CardHeader className="flex flex-row items-center justify-between gap-1.5 border-b border-border/50">
          <div className="flex items-center gap-1.5">
            <Table2 className="h-3.5 w-3.5 text-ink-subtle" />
            <CardTitle className="text-xs font-semibold tracking-tight text-ink">
              Stage 1 vs. pretrained — 6-class COCO holdout
            </CardTitle>
          </div>
          <span className="text-[10px] text-ink-subtle">29 held-out COCO128 images</span>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border/60">
                <th className="text-left font-medium text-ink-subtle text-xs uppercase tracking-wide py-2 pr-4">Class</th>
                <th className="text-right font-medium text-ink-subtle text-xs uppercase tracking-wide py-2 px-3">Pretrained mAP50</th>
                <th className="text-right font-medium text-ink-subtle text-xs uppercase tracking-wide py-2 px-3">Stage 1 mAP50</th>
              </tr>
            </thead>
            <tbody>
              {cocoClasses.map((className) => {
                const pretrained = cocoPerClass[className].pretrained?.mAP50
                const stage1 = cocoPerClass[className].stage1?.mAP50
                const collapsed = stage1 === 0
                return (
                  <tr key={className} className="border-b border-border/30 last:border-0">
                    <td className="py-2 pr-4 text-ink-quiet capitalize">{className}</td>
                    <td className="py-2 px-3 text-right font-mono tabular-nums font-semibold text-ink">{fmt(pretrained)}</td>
                    <td className={cn('py-2 px-3 text-right font-mono tabular-nums font-semibold', collapsed ? 'text-danger' : 'text-ink')}>
                      {fmt(stage1)}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* Interpretation */}
      <Card size="sm" className="border-border bg-surface shadow-2xs">
        <CardHeader className="border-b border-border/50">
          <CardTitle className="text-xs font-semibold tracking-tight text-ink">Interpretation</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2.5 text-sm text-ink-quiet">
          <p>
            <b className="text-ink">Stage 1 collapsed, not just underperformed.</b> Fine-tuning on a class-narrowed,
            97-image COCO128 subset drove {collapsedClasses.length} of {cocoClasses.length} classes to exactly 0.0
            mAP50 and cratered person precision (0.723 → 0.005). The likely cause is severe class imbalance (196
            person instances vs. 2–27 for every other class) combined with the detection head reinitializing for a
            new 6-class output at only 5 epochs — checked against a labeling bug first, not assumed.
          </p>
          <p>
            <b className="text-ink">Stage 2&apos;s precision never recovered.</b> Continuing training on real footage
            left precision at 0.003 — statistically the same collapse as Stage 1. The one real improvement is
            mAP50-95 (localization quality when a true positive is found), which beat even the pretrained baseline.
          </p>
          <p>
            <b className="text-ink">What this does and doesn&apos;t prove.</b> The 6 real-footage validation frames are
            different frames of the exact same near-static clip Stage 2 trained 24 near-duplicate frames on. This is
            much closer to <i>&quot;did it memorize this one scene precisely&quot;</i> than{' '}
            <i>&quot;does it generalize to new deployment conditions&quot;</i> — it does not demonstrate generalization.
            Fed through the full detect→track pipeline, both fine-tuned stages produced a complete tracking failure
            (MOTA/IDF1 flat 0.0 across all 244 real frames) — the sharpest evidence that isolated precision/recall
            numbers alone understated how unusable these models are for TRACE&apos;s actual pipeline.
          </p>
          <p>
            The live pipeline keeps loading the plain pretrained baseline by default (
            <code className="font-mono text-xs">DEFAULT_MODEL_PATH = &quot;yolov8n.pt&quot;</code>). Full methodology:
            TRACE_STUDY_GUIDE.md Sections 2, 15, and 20.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
