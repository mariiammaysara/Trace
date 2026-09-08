import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import userEvent from '@testing-library/user-event'
import { UploadVideoModal } from './UploadVideoModal'
import * as api from '@/lib/api'

function makeFile(name: string, type = 'video/mp4') {
  return new File(['fake video bytes'], name, { type })
}

describe('UploadVideoModal', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders nothing when closed', () => {
    render(<UploadVideoModal isOpen={false} onClose={vi.fn()} onUploaded={vi.fn()} />)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('idle state: submit is disabled until a file and camera id are provided', async () => {
    const user = userEvent.setup()
    render(<UploadVideoModal isOpen={true} onClose={vi.fn()} onUploaded={vi.fn()} />)

    const submit = screen.getByRole('button', { name: /^Upload$/i })
    expect(submit).toBeDisabled()

    await user.upload(screen.getByLabelText(/Video file/i), makeFile('clip.mp4'))
    expect(submit).toBeDisabled() // camera id still empty

    await user.type(screen.getByLabelText(/Camera ID/i), 'front-door')
    expect(submit).not.toBeDisabled()
  })

  it('uploading state: shows a spinner and disables the form while the request is in flight, then calls onUploaded + onClose on success', async () => {
    const user = userEvent.setup()
    let resolveUpload!: (video: api.Video) => void
    vi.spyOn(api, 'uploadVideo').mockReturnValue(
      new Promise<api.Video>((resolve) => {
        resolveUpload = resolve
      }),
    )

    const onUploaded = vi.fn()
    const onClose = vi.fn()
    render(<UploadVideoModal isOpen={true} onClose={onClose} onUploaded={onUploaded} />)

    await user.upload(screen.getByLabelText(/Video file/i), makeFile('clip.mp4'))
    await user.type(screen.getByLabelText(/Camera ID/i), 'front-door')
    await user.click(screen.getByRole('button', { name: /^Upload$/i }))

    expect(screen.getByText(/Uploading/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Camera ID/i)).toBeDisabled()

    resolveUpload({
      id: 7, camera_id: 1, path: 'data/uploads/x.mp4', started_at: null,
      status: 'pending', total_frames: 100, frames_processed: 0, current_fps: null, error_message: null,
    })

    await waitFor(() => expect(onUploaded).toHaveBeenCalledWith(
      expect.objectContaining({ id: 7, status: 'pending' }), 'front-door', 'clip.mp4',
    ))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('error state: a rejected upload (e.g. oversized/unsupported format from the backend) shows the real error and keeps the modal open', async () => {
    const user = userEvent.setup()
    vi.spyOn(api, 'uploadVideo').mockRejectedValue(new Error('file exceeds the 200MB upload limit'))

    const onClose = vi.fn()
    render(<UploadVideoModal isOpen={true} onClose={onClose} onUploaded={vi.fn()} />)

    await user.upload(screen.getByLabelText(/Video file/i), makeFile('clip.mp4'))
    await user.type(screen.getByLabelText(/Camera ID/i), 'front-door')
    await user.click(screen.getByRole('button', { name: /^Upload$/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/file exceeds the 200MB upload limit/i)
    expect(onClose).not.toHaveBeenCalled()
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('rejects an unsupported file extension client-side before ever calling the API', async () => {
    // applyAccept: false -- the input's accept=".mp4,.mov,..." already steers
    // a real file picker away from this; this test is for the component's
    // own defense-in-depth extension check, not the browser's.
    const user = userEvent.setup({ applyAccept: false })
    const uploadSpy = vi.spyOn(api, 'uploadVideo')

    render(<UploadVideoModal isOpen={true} onClose={vi.fn()} onUploaded={vi.fn()} />)

    await user.upload(screen.getByLabelText(/Video file/i), makeFile('notes.txt', 'text/plain'))
    await user.type(screen.getByLabelText(/Camera ID/i), 'front-door')
    await user.click(screen.getByRole('button', { name: /^Upload$/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/unsupported format/i)
    expect(uploadSpy).not.toHaveBeenCalled()
  })
})
