import { useEffect, useState } from 'react'
import { getVideoStatus } from '@/lib/api'
import type { VideoStatus } from '@/lib/api'

const POLL_INTERVAL_MS = 2000

/**
 * Polls GET /videos/{id}/status while a video is still pending/processing --
 * plain polling (Step 1's deferred-work note: no WebSockets/SSE needed at
 * this scale). Stops automatically once the backend reports a terminal
 * status ("done"/"failed"), so an upload that finished minutes ago doesn't
 * keep quietly hitting the API forever.
 */
export function useVideoStatus(videoId: number | null): { status: VideoStatus | null; error: string | null } {
  const [status, setStatus] = useState<VideoStatus | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (videoId === null) return
    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | undefined

    const poll = () => {
      getVideoStatus(videoId)
        .then((result) => {
          if (cancelled) return
          setStatus(result)
          setError(null)
          if (result.status === 'pending' || result.status === 'processing') {
            timer = setTimeout(poll, POLL_INTERVAL_MS)
          }
        })
        .catch((err: unknown) => {
          if (!cancelled) setError(String(err))
        })
    }

    poll()

    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
    }
  }, [videoId])

  return { status, error }
}
