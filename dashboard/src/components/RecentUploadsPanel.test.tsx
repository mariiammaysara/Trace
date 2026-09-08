import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import userEvent from '@testing-library/user-event'
import { RecentUploadsPanel, type UploadEntry } from './RecentUploadsPanel'
import * as api from '@/lib/api'

function upload(overrides: Partial<UploadEntry> = {}): UploadEntry {
  return { videoId: 1, cameraId: 'cam_a', filename: 'clip.mp4', createdAt: Date.now(), ...overrides }
}

describe('RecentUploadsPanel', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders nothing when there are no uploads', () => {
    const { container } = render(<RecentUploadsPanel uploads={[]} onViewLive={vi.fn()} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('pending state: shows a spinner badge before any frames have been processed', async () => {
    vi.spyOn(api, 'getVideoStatus').mockResolvedValue({
      id: 1, status: 'pending', total_frames: 100, frames_processed: 0,
      percent: 0, current_fps: null, eta_seconds: null, error_message: null,
    })

    render(<RecentUploadsPanel uploads={[upload()]} onViewLive={vi.fn()} />)

    expect(await screen.findByText('pending')).toBeInTheDocument()
    expect(screen.getByText('clip.mp4')).toBeInTheDocument()
  })

  it('processing state: shows real percent, frame counts, FPS, and ETA from the API response', async () => {
    vi.spyOn(api, 'getVideoStatus').mockResolvedValue({
      id: 1, status: 'processing', total_frames: 100, frames_processed: 25,
      percent: 25, current_fps: 10, eta_seconds: 7.5, error_message: null,
    })

    render(<RecentUploadsPanel uploads={[upload()]} onViewLive={vi.fn()} />)

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

    render(<RecentUploadsPanel uploads={[upload({ cameraId: 'cam_done' })]} onViewLive={onViewLive} />)

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

    render(<RecentUploadsPanel uploads={[upload()]} onViewLive={vi.fn()} />)

    expect(await screen.findByText('failed')).toBeInTheDocument()
    expect(screen.getByText('could not open frame source')).toBeInTheDocument()
  })

  it('surfaces a fetch failure without crashing the panel', async () => {
    vi.spyOn(api, 'getVideoStatus').mockRejectedValue(new Error('network error'))

    render(<RecentUploadsPanel uploads={[upload()]} onViewLive={vi.fn()} />)

    await waitFor(() => expect(screen.getByText(/Couldn't reach status endpoint/i)).toBeInTheDocument())
  })
})
