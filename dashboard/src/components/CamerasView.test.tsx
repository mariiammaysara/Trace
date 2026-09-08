import { render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import userEvent from '@testing-library/user-event'
import { CamerasView } from './CamerasView'
import * as api from '@/lib/api'
import type { Camera } from '@/lib/api'

const cameras: Camera[] = [
  { id: 1, camera_id: 'front-entrance', name: 'Front Entrance', location: null, calibration_reference: null },
  { id: 2, camera_id: 'demo', name: null, location: null, calibration_reference: null },
]

const sampleCounts: api.CameraDeletionCounts = {
  alerts: 0, events: 3, track_points: 10, objects: 1, videos: 1, zones: 0, lines: 0,
}

function renderView(overrides: Partial<React.ComponentProps<typeof CamerasView>> = {}) {
  return render(
    <CamerasView
      cameras={cameras}
      selectedCameraId={null}
      onSelectCamera={vi.fn()}
      {...overrides}
    />,
  )
}

describe('CamerasView delete action', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(api, 'listCameraObjects').mockResolvedValue([])
    vi.spyOn(api, 'listCameraEvents').mockResolvedValue([])
    vi.spyOn(api, 'listVideos').mockResolvedValue([])
  })

  it('opens the delete confirmation for the row that was clicked, with that camera real preview counts', async () => {
    vi.spyOn(api, 'getCameraDeletionPreview').mockResolvedValue(sampleCounts)
    const user = userEvent.setup()

    renderView()

    const deleteButtons = screen.getAllByRole('button', { name: /^Delete camera/i })
    await user.click(deleteButtons[0])

    expect(api.getCameraDeletionPreview).toHaveBeenCalledWith('front-entrance')
    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByText('front-entrance')).toBeInTheDocument()
    // no reference-camera warning for this one
    expect(screen.queryByText(/documented reference camera/i)).not.toBeInTheDocument()
  })

  it('requires the extra typed confirmation when deleting the "demo" row specifically', async () => {
    vi.spyOn(api, 'getCameraDeletionPreview').mockResolvedValue(sampleCounts)
    const user = userEvent.setup()

    renderView()

    await user.click(screen.getByRole('button', { name: 'Delete camera demo' }))

    await waitFor(() => expect(screen.getByText(/documented reference camera/i)).toBeInTheDocument())
    expect(screen.getByRole('button', { name: /^Delete camera$/i })).toBeDisabled()
  })

  it('calls onCameraDeleted with the real deleted counts after a successful delete', async () => {
    vi.spyOn(api, 'getCameraDeletionPreview').mockResolvedValue(sampleCounts)
    vi.spyOn(api, 'deleteCamera').mockResolvedValue(sampleCounts)
    const onCameraDeleted = vi.fn()
    const user = userEvent.setup()

    renderView({ onCameraDeleted })

    await user.click(screen.getByRole('button', { name: 'Delete camera front-entrance' }))
    const confirmBtn = await screen.findByRole('button', { name: /^Delete camera$/i })
    await user.click(confirmBtn)

    await waitFor(() => expect(onCameraDeleted).toHaveBeenCalledWith('front-entrance', sampleCounts))
  })
})
