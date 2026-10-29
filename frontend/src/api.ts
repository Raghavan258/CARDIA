const API_BASE = ''

export async function fetchHealth(): Promise<{ status: string; version: string }> {
  const r = await fetch(`${API_BASE}/api/health`)
  if (!r.ok) throw new Error(`Health check failed (${r.status})`)
  return r.json()
}

export async function createSession(body: {
  algorithm?: 'pos' | 'chrom'
  input_mode?: 'live' | 'recorded'
  max_width?: number
  target_fps?: number
}): Promise<{ session_id: string; ws_url: string; state: string }> {
  const r = await fetch(`${API_BASE}/api/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      algorithm: body.algorithm ?? 'pos',
      input_mode: body.input_mode ?? 'live',
      max_width: body.max_width ?? 640,
      target_fps: body.target_fps ?? 8,
    }),
  })
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }))
    throw new Error(err.detail || 'Failed to create session')
  }
  return r.json()
}

export async function stopSession(sessionId: string): Promise<void> {
  await fetch(`${API_BASE}/api/sessions/${sessionId}/stop`, { method: 'POST' })
}

export function wsUrl(path: string): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}${path}`
}
