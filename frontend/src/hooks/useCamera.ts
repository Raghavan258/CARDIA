import { useCallback, useEffect, useRef, useState } from 'react'

export type CameraStatus = 'idle' | 'requesting' | 'ready' | 'denied' | 'error'

/**
 * Acquire a webcam stream via getUserMedia and expose a video element ref.
 */
export function useCamera() {
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const [status, setStatus] = useState<CameraStatus>('idle')
  const [error, setError] = useState<string | null>(null)

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    if (videoRef.current) videoRef.current.srcObject = null
    setStatus('idle')
  }, [])

  const start = useCallback(async (): Promise<boolean> => {
    setError(null)
    setStatus('requesting')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'user',
          width: { ideal: 640 },
          height: { ideal: 480 },
        },
        audio: false,
      })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }
      setStatus('ready')
      return true
    } catch (e) {
      const name = e instanceof DOMException ? e.name : 'Error'
      if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
        setStatus('denied')
        setError('Camera permission denied. Allow camera access and try again.')
      } else {
        setStatus('error')
        setError(e instanceof Error ? e.message : 'Camera unavailable')
      }
      stop()
      return false
    }
  }, [stop])

  useEffect(() => () => stop(), [stop])

  return { videoRef, status, error, start, stop }
}
