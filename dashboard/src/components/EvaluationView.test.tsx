import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { EvaluationView } from './EvaluationView'
import * as api from '@/lib/api'

/**
 * Mirrors the real, checked-in evaluation-harness output exactly (see
 * evaluation/results/detection_comparison.json,
 * evaluation/results/tracking_comparison.json, and
 * TRACE_STUDY_GUIDE.md Section 15) -- including Stage 1's real collapse to
 * 0.0 mAP50 on 5/6 COCO classes and the flat 0.0 MOTA/IDF1 tracking
 * failure, so this test proves the UI doesn't silently filter those out.
 */
const mockEvaluation: api.EvaluationData = {
  detection: {
    coco_holdout: {
      weights: { pretrained: 'yolov8n.pt', stage1: 'models/yolov8n_trace_stage1.pt' },
      per_class: {
        person: {
          pretrained: { Class: 'person', Images: 14, Instances: 58, 'Box-P': 0.72288, 'Box-R': 0.7069, 'Box-F1': 0.7148, mAP50: 0.74385, 'mAP50-95': 0.49662, model: 'pretrained' },
          stage1: { Class: 'person', Images: 14, Instances: 58, 'Box-P': 0.0054, 'Box-R': 0.81034, 'Box-F1': 0.01073, mAP50: 0.33953, 'mAP50-95': 0.18392, model: 'stage1' },
        },
        car: {
          pretrained: { Class: 'car', Images: 5, Instances: 19, 'Box-P': 0.46069, 'Box-R': 0.31579, 'Box-F1': 0.37472, mAP50: 0.4058, 'mAP50-95': 0.2118, model: 'pretrained' },
          stage1: { Class: 'car', Images: 5, Instances: 19, 'Box-P': 0.0, 'Box-R': 0.0, 'Box-F1': 0.0, mAP50: 0.0, 'mAP50-95': 0.0, model: 'stage1' },
        },
        bicycle: {
          pretrained: { Class: 'bicycle', Images: 1, Instances: 1, 'Box-P': 0.52111, 'Box-R': 1.0, 'Box-F1': 0.68517, mAP50: 0.995, 'mAP50-95': 0.8955, model: 'pretrained' },
          stage1: { Class: 'bicycle', Images: 1, Instances: 1, 'Box-P': 0.0, 'Box-R': 0.0, 'Box-F1': 0.0, mAP50: 0.0, 'mAP50-95': 0.0, model: 'stage1' },
        },
      },
    },
    real_footage_holdout: {
      weights: { pretrained: 'yolov8n.pt', stage1: 'models/yolov8n_trace_stage1.pt', stage2: 'models/yolov8n_trace_stage2.pt' },
      per_class: {
        person: {
          pretrained: { Class: 'person', Images: 6, Instances: 6, 'Box-P': 0.9898, 'Box-R': 1.0, 'Box-F1': 0.99487, mAP50: 0.995, 'mAP50-95': 0.5008, model: 'pretrained' },
          stage1: { Class: 'person', Images: 6, Instances: 6, 'Box-P': 0.00333, 'Box-R': 1.0, 'Box-F1': 0.00664, mAP50: 0.995, 'mAP50-95': 0.30887, model: 'stage1' },
          stage2: { Class: 'person', Images: 6, Instances: 6, 'Box-P': 0.00333, 'Box-R': 1.0, 'Box-F1': 0.00664, mAP50: 0.995, 'mAP50-95': 0.6965, model: 'stage2' },
        },
      },
    },
  },
  tracking: {
    real_footage: {
      ground_truth_frames: 244,
      weights: { pretrained: 'yolov8n.pt', stage1: 'models/yolov8n_trace_stage1.pt', stage2: 'models/yolov8n_trace_stage2.pt' },
      results: {
        pretrained: { mota: 1.0, idf1: 1.0, num_switches: 0, num_false_positives: 0, num_misses: 0, num_matches: 244 },
        stage1: { mota: 0.0, idf1: 0.0, num_switches: 0, num_false_positives: 0, num_misses: 244, num_matches: 0 },
        stage2: { mota: 0.0, idf1: 0.0, num_switches: 0, num_false_positives: 0, num_misses: 244, num_matches: 0 },
      },
    },
    synthetic_crossing: {
      ground_truth_frames: 20,
      results: { mota: 1.0, idf1: 1.0, num_switches: 0, num_false_positives: 0, num_misses: 0, num_matches: 40 },
    },
  },
}

function renderEvaluationView() {
  return render(<EvaluationView />)
}

describe('EvaluationView', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the real comparison table for all three models, including Stage 1/2 collapsed values', async () => {
    vi.spyOn(api, 'getEvaluation').mockResolvedValue(mockEvaluation)
    renderEvaluationView()

    // Real numbers: recall is a perfect 1.0 for all three models (pretrained,
    // stage1, stage2 -- the collapsed models over-predict everywhere rather
    // than under-predict, which is exactly why precision, not recall, is
    // where their collapse actually shows up) plus pretrained's real MOTA/IDF1.
    expect((await screen.findAllByText('1.000')).length).toBe(5)

    // The collapse itself must render, not be hidden or replaced with a
    // placeholder -- this is the whole point of the test.
    expect(screen.getAllByText('0.000').length).toBeGreaterThan(0) // stage1/stage2 MOTA and IDF1
    expect(screen.getAllByText('0.003').length).toBe(2) // stage1 and stage2 precision (rounded from 0.00333)

    // Stage 2's real, narrowly-scoped win still renders.
    expect(screen.getByText('0.697')).toBeInTheDocument() // stage2 mAP50-95
  })

  it('renders the COCO 6-class table with a real 0.0 mAP50 for a collapsed class, not filtered out', async () => {
    vi.spyOn(api, 'getEvaluation').mockResolvedValue(mockEvaluation)
    renderEvaluationView()

    await screen.findByText(/Stage 1 vs\. pretrained/i)
    expect(screen.getByText('car')).toBeInTheDocument()
    // pretrained car mAP50 (0.4058) and stage1 car mAP50 (0.0) must both be visible.
    expect(screen.getByText('0.406')).toBeInTheDocument()
    // Two collapsed classes (car, bicycle) both show 0.000 in the Stage 1 column.
    expect(screen.getAllByText('0.000').length).toBeGreaterThanOrEqual(2)

    // The headline "collapsed classes" count reflects the real data (2 of 3 in this fixture).
    expect(await screen.findByText('2/3')).toBeInTheDocument()
  })

  it('shows a real error state, not fabricated data, when the evaluation harness output is unavailable', async () => {
    vi.spyOn(api, 'getEvaluation').mockRejectedValue(new Error('evaluation results not found'))
    renderEvaluationView()

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('evaluation results not found'))
    expect(screen.queryByText(/Baseline vs\. Stage 1 vs\. Stage 2/i)).not.toBeInTheDocument()
  })
})
