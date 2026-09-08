import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import userEvent from '@testing-library/user-event'
import { RecentUploadsPanel, type UploadEntry } from './RecentUploadsPanel'
import * as api from '@/lib/api'

function upload(overrides: Partial<UploadEntry> = {}): UploadEntry {
  return { videoId: 1, cameraId: 'cam_a', filename: 'clip.mp4', createdAt: Date.now(), ...overrides }
}

function renderPanel(uploads: UploadEntry[], overrides: { onViewLive?: () => void; onRequestDelete?: (cameraId: string) => void } = {}) {
  return render(
    <RecentUploadsPanel
      uploads={uploads}
      onViewLive={overrides.onViewLive ?? vi.fn()}
      onRequestDelete={overrides.onRequestDelete ?? vi.fn()}
    />,
  )
}

describe('RecentUploadsPanel', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders nothing when there are no uploads', () => {
    const { container } = renderPanel([])
    expect(container).toBeEmptyDOMElement()
  })

  it('pending state: shows a spinner badge before any frames have been processed', async () => {
    vi.spyOn(api, 'getVideoStatus').mockResolvedValue({
      id: 1, status: 'pending', total_frames: 100, frames_processed: 0,
      percent: 0, current_fps: null, eta_seconds: null, error_message: null,
    })

    renderPanel([upload()])

    expect(await screen.findByText('pending')).toBeInTheDocument()
    expect(screen.getByText('clip.mp4')).toBeInTheDocument()
  })

  it('processing state: shows real percent, frame counts, FPS, and ETA from the API response', async () => {
    vi.spyOn(api, 'getVideoStatus').mockResolvedValue({
      id: 1, status: 'processing', total_frames: 100, frames_processed: 25,
      percent: 25, current_fps: 10, eta_seconds: 7.5, error_message: null,
    })

    renderPanel([upload()])

    expect(await screen.findByText('processing')).toBeInTheDocument()
    expect(screen.getByText('25 / 100 frames')).toBeInTheDocument()
    expect(screen.getByText('10.0 FPS')).toBeInTheDocument()
    expect(screen.getByText(/~8s left/)).toBeInTheDocument()
  })

  it('done state: shows a View Live button that navigates to the right camera', async () => {
    vi.spyOn(api, 'getVideoStatus').mockResolvedValue({
      id: 1, status: 'done', total_frames: 100, frames_processed: 100,
      percent: 100, current_fps: 12.3, eta_seconds: null, error_message: null,
    })
    const onViewLive = vi.fn()
    const user = userEvent.setup()

    renderPanel([upload({ cameraId: 'cam_done' })], { onViewLive })

    const viewLiveBtn = await screen.findByRole('button', { name: /View Live/i })
    await user.click(viewLiveBtn)
    expect(onViewLive).toHaveBeenCalledWith('cam_done')
  })

  it('error state: shows the real backend error message, not a generic failure', async () => {
    vi.spyOn(api, 'getVideoStatus').mockResolvedValue({
      id: 1, status: 'failed', total_frames: 100, frames_processed: 40,
      percent: 40, current_fps: null, eta_seconds: null,
      error_message: 'could not open frame source',
    })

    renderPanel([upload()])

    expect(await screen.findByText('failed')).toBeInTheDocument()
    expect(screen.getByText('could not open frame source')).toBeInTheDocument()
  })

  it('surfaces a fetch failure without crashing the panel', async () => {
    vi.spyOn(api, 'getVideoStatus').mockRejectedValue(new Error('network error'))

    renderPanel([upload()])

    await waitFor(() => expect(screen.getByText(/Couldn't reach status endpoint/i)).toBeInTheDocument())
  })

  it('clicking the delete button requests deletion of the underlying camera, not just the upload row', async () => {
    vi.spyOn(api, 'getVideoStatus').mockResolvedValue({
      id: 1, status: 'done', total_frames: 100, frames_processed: 100,
      percent: 100, current_fps: 12.3, eta_seconds: null, error_message: null,
    })
    const onRequestDelete = vi.fn()
    const user = userEvent.setup()

    renderPanel([upload({ cameraId: 'cam_to_delete' })], { onRequestDelete })

    const deleteBtn = await screen.findByRole('button', { name: /Delete camera cam_to_delete/i })
    await user.click(deleteBtn)
    expect(onRequestDelete).toHaveBeenCalledWith('cam_to_delete')
  })
})
