import { useCallback, useEffect, useRef, useState } from 'react'
import { createSession, stopSession, wsUrl } from '../api'
import type { ServerMessage, VitalsPayload } from '../types'

const TARGET_FPS = 8
const JPEG_QUALITY = 0.65
const MAX_IN_FLIGHT = 1

type ConnStatus = 'disconnected' | 'connecting' | 'connected' | 'error'

/**
 * Owns session lifecycle, WebSocket I/O, and throttled JPEG frame upload.
 */
export function useMonitorSession(videoRef: React.RefObject<HTMLVideoElement | null>) {
  const [conn, setConn] = useState<ConnStatus>('disconnected')
  const [backendOk, setBackendOk] = useState<boolean | null>(null)
  const [vitals, setVitals] = useState<VitalsPayload | null>(null)
  const [latencyMs, setLatencyMs] = useState<number | null>(null)
  const [drops, setDrops] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [running, setRunning] = useState(false)
  const [algorithm, setAlgorithm] = useState<'pos' | 'chrom'>('pos')

  const wsRef = useRef<WebSocket | null>(null)
  const sessionIdRef = useRef<string | null>(null)
  const loopRef = useRef<number | null>(null)
  const inFlightRef = useRef(0)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const startedAtRef = useRef<number | null>(null)

  const cleanupLoop = useCallback(() => {
    if (loopRef.current != null) {
      window.clearInterval(loopRef.current)
      loopRef.current = null
    }
    inFlightRef.current = 0
  }, [])

  const disconnectWs = useCallback(() => {
    cleanupLoop()
    const ws = wsRef.current
    wsRef.current = null
    if (ws && ws.readyState <= WebSocket.OPEN) {
      try {
        ws.send(JSON.stringify({ type: 'stop' }))
      } catch {
        /* ignore */
      }
      ws.close()
    }
  }, [cleanupLoop])

  const stop = useCallback(async () => {
    setRunning(false)
    disconnectWs()
    const sid = sessionIdRef.current
    sessionIdRef.current = null
    if (sid) {
      try {
        await stopSession(sid)
      } catch {
        /* ignore */
      }
    }
    setConn('disconnected')
    startedAtRef.current = null
  }, [disconnectWs])

  const sendFrame = useCallback(() => {
    const ws = wsRef.current
    const video = videoRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN || !video) return
    if (video.readyState < 2) return
    if (inFlightRef.current >= MAX_IN_FLIGHT) {
      setDrops((d) => d + 1)
      return
    }

    if (!canvasRef.current) canvasRef.current = document.createElement('canvas')
    const canvas = canvasRef.current
    const w = Math.min(640, video.videoWidth || 640)
    const h = Math.round(((video.videoHeight || 480) / (video.videoWidth || 640)) * w)
    canvas.width = w
    canvas.height = h
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.drawImage(video, 0, 0, w, h)

    inFlightRef.current += 1
    const t0 = performance.now()
    canvas.toBlob(
      (blob) => {
        if (!blob || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
          inFlightRef.current = Math.max(0, inFlightRef.current - 1)
          return
        }
        const reader = new FileReader()
        reader.onload = () => {
          const result = reader.result as string
          const b64 = result.split(',')[1] || ''
          try {
            wsRef.current?.send(
              JSON.stringify({
                type: 'frame',
                timestamp_s: (performance.now() - (startedAtRef.current || t0)) / 1000,
                mime: 'image/jpeg',
                data_base64: b64,
              }),
            )
          } finally {
            inFlightRef.current = Math.max(0, inFlightRef.current - 1)
          }
        }
        reader.onerror = () => {
          inFlightRef.current = Math.max(0, inFlightRef.current - 1)
        }
        reader.readAsDataURL(blob)
      },
      'image/jpeg',
      JPEG_QUALITY,
    )
  }, [videoRef])

  const start = useCallback(async () => {
    setError(null)
    setDrops(0)
    setVitals(null)
    setConn('connecting')
    setRunning(true)
    try {
      const session = await createSession({ algorithm, target_fps: TARGET_FPS, max_width: 640 })
      sessionIdRef.current = session.session_id
      const ws = new WebSocket(wsUrl(session.ws_url))
      wsRef.current = ws

      ws.onopen = () => {
        setConn('connected')
        setBackendOk(true)
        startedAtRef.current = performance.now()
        cleanupLoop()
        loopRef.current = window.setInterval(sendFrame, Math.round(1000 / TARGET_FPS))
      }
      ws.onmessage = (ev) => {
        const msg = JSON.parse(ev.data) as ServerMessage
        if (msg.type === 'vitals') {
          setVitals(msg.payload)
          setLatencyMs(msg.latency_ms)
          setDrops(msg.stats.frames_dropped)
        } else if (msg.type === 'error') {
          setError(msg.message)
        }
      }
      ws.onerror = () => {
        setConn('error')
        setBackendOk(false)
        setError('WebSocket connection error')
      }
      ws.onclose = () => {
        cleanupLoop()
        setConn((c) => (c === 'error' ? c : 'disconnected'))
        setRunning(false)
      }
    } catch (e) {
      setRunning(false)
      setConn('error')
      setBackendOk(false)
      setError(e instanceof Error ? e.message : 'Failed to start session')
    }
  }, [algorithm, cleanupLoop, sendFrame])

  useEffect(() => () => {
    void stop()
  }, [stop])

  return {
    running,
    conn,
    backendOk,
    vitals,
    latencyMs,
    drops,
    error,
    algorithm,
    setAlgorithm,
    start,
    stop,
  }
}
