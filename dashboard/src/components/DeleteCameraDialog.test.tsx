import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import userEvent from '@testing-library/user-event'
import { DeleteCameraDialog } from './DeleteCameraDialog'
import * as api from '@/lib/api'

const sampleCounts: api.CameraDeletionCounts = {
  alerts: 1, events: 5, track_points: 40, objects: 3, videos: 2, zones: 1, lines: 1,
}

describe('DeleteCameraDialog', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders nothing when cameraId is null', () => {
    render(<DeleteCameraDialog cameraId={null} onClose={vi.fn()} onDeleted={vi.fn()} />)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('fetches and shows the real preview counts for an ordinary camera, and enables delete with a single click (no typed confirmation)', async () => {
    vi.spyOn(api, 'getCameraDeletionPreview').mockResolvedValue(sampleCounts)
    vi.spyOn(api, 'deleteCamera').mockResolvedValue(sampleCounts)
    const onDeleted = vi.fn()
    const onClose = vi.fn()
    const user = userEvent.setup()

    render(<DeleteCameraDialog cameraId="front-entrance" onClose={onClose} onDeleted={onDeleted} />)

    expect(api.getCameraDeletionPreview).toHaveBeenCalledWith('front-entrance')
    await waitFor(() => expect(screen.getByText('5')).toBeInTheDocument()) // events count
    expect(screen.getByText('40')).toBeInTheDocument() // track_points count

    // no reference-camera warning, no typed-confirmation field for a normal camera
    expect(screen.queryByText(/documented reference camera/i)).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/Type ".*" to confirm/i)).not.toBeInTheDocument()

    const deleteBtn = screen.getByRole('button', { name: /Delete camera/i })
    expect(deleteBtn).not.toBeDisabled()

    await user.click(deleteBtn)

    await waitFor(() => expect(api.deleteCamera).toHaveBeenCalledWith('front-entrance'))
    expect(onDeleted).toHaveBeenCalledWith('front-entrance', sampleCounts)
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('requires typing the exact camera name for "demo", and shows the extra reference-camera warning', async () => {
    vi.spyOn(api, 'getCameraDeletionPreview').mockResolvedValue(sampleCounts)
    vi.spyOn(api, 'deleteCamera').mockResolvedValue(sampleCounts)
    const user = userEvent.setup()

    render(<DeleteCameraDialog cameraId="demo" onClose={vi.fn()} onDeleted={vi.fn()} />)

    await waitFor(() => expect(screen.getByText(/documented reference camera/i)).toBeInTheDocument())
    expect(screen.getByText(/README\.md and TRACE_STUDY_GUIDE\.md/)).toBeInTheDocument()

    const deleteBtn = screen.getByRole('button', { name: /Delete camera/i })
    expect(deleteBtn).toBeDisabled()

    const confirmInput = screen.getByLabelText(/Type "demo" to confirm/i)
    await user.type(confirmInput, 'dem')
    expect(deleteBtn).toBeDisabled() // partial match still blocks it

    await user.type(confirmInput, 'o')
    expect(deleteBtn).not.toBeDisabled()

    await user.click(deleteBtn)
    await waitFor(() => expect(api.deleteCamera).toHaveBeenCalledWith('demo'))
  })

  it('requires the exact typed name for "demo-trafficlight" too, not just any non-empty text', async () => {
    vi.spyOn(api, 'getCameraDeletionPreview').mockResolvedValue(sampleCounts)
    const user = userEvent.setup()

    render(<DeleteCameraDialog cameraId="demo-trafficlight" onClose={vi.fn()} onDeleted={vi.fn()} />)

    await waitFor(() => expect(screen.getByText(/documented reference camera/i)).toBeInTheDocument())

    const confirmInput = screen.getByLabelText(/Type "demo-trafficlight" to confirm/i)
    const deleteBtn = screen.getByRole('button', { name: /Delete camera/i })

    await user.type(confirmInput, 'demo-traffic')
    expect(deleteBtn).toBeDisabled()

    await user.type(confirmInput, 'light')
    expect(deleteBtn).not.toBeDisabled()
  })

  it('does not require typed confirmation for a similarly-named but different camera id', async () => {
    vi.spyOn(api, 'getCameraDeletionPreview').mockResolvedValue(sampleCounts)
    render(<DeleteCameraDialog cameraId="demo-2" onClose={vi.fn()} onDeleted={vi.fn()} />)

    await waitFor(() => expect(screen.getByRole('button', { name: /Delete camera/i })).not.toBeDisabled())
    expect(screen.queryByText(/documented reference camera/i)).not.toBeInTheDocument()
  })

  it('shows a real error and keeps the dialog open if the preview fetch fails', async () => {
    vi.spyOn(api, 'getCameraDeletionPreview').mockRejectedValue(new Error('no camera with camera_id=\'gone\''))

    render(<DeleteCameraDialog cameraId="gone" onClose={vi.fn()} onDeleted={vi.fn()} />)

    expect(await screen.findByRole('alert')).toHaveTextContent("no camera with camera_id='gone'")
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('shows a real error and keeps the dialog open if the delete call itself fails', async () => {
    vi.spyOn(api, 'getCameraDeletionPreview').mockResolvedValue(sampleCounts)
    vi.spyOn(api, 'deleteCamera').mockRejectedValue(new Error('internal server error'))
    const onDeleted = vi.fn()
    const onClose = vi.fn()
    const user = userEvent.setup()

    render(<DeleteCameraDialog cameraId="front-entrance" onClose={onClose} onDeleted={onDeleted} />)

    const deleteBtn = await screen.findByRole('button', { name: /Delete camera/i })
    await user.click(deleteBtn)

    expect(await screen.findByRole('alert')).toHaveTextContent('internal server error')
    expect(onDeleted).not.toHaveBeenCalled()
    expect(onClose).not.toHaveBeenCalled()
  })

  it('calls onClose when Cancel is clicked', async () => {
    vi.spyOn(api, 'getCameraDeletionPreview').mockResolvedValue(sampleCounts)
    const onClose = vi.fn()
    const user = userEvent.setup()

    render(<DeleteCameraDialog cameraId="front-entrance" onClose={onClose} onDeleted={vi.fn()} />)
    await user.click(screen.getByRole('button', { name: /^Cancel$/i }))
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
