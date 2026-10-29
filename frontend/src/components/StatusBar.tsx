type Props = {
  backendOk: boolean | null
  conn: string
  state: string
  elapsedS: number | null
  latencyMs: number | null
  effectiveFps: number | null
  drops: number
}

export function StatusBar(props: Props) {
  const backendLabel =
    props.backendOk == null ? 'Backend: unknown' : props.backendOk ? 'Backend: online' : 'Backend: offline'
  const elapsed =
    props.elapsedS == null ? '--:--' : formatElapsed(props.elapsedS)

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-[var(--muted)]">
      <span className="inline-flex items-center gap-2">
        <StatusDot ok={props.backendOk === true} />
        <span className="text-[var(--ink)]">{backendLabel}</span>
      </span>
      <span>Connection: <strong className="font-medium text-[var(--ink)]">{props.conn}</strong></span>
      <span>State: <strong className="font-medium text-[var(--ink)]">{props.state}</strong></span>
      <span>Elapsed: <strong className="font-medium text-[var(--ink)]">{elapsed}</strong></span>
      <span>Latency: <strong className="font-medium text-[var(--ink)]">{props.latencyMs?.toFixed(0) ?? '—'} ms</strong></span>
      <span>Eff. FPS: <strong className="font-medium text-[var(--ink)]">{props.effectiveFps?.toFixed(1) ?? '—'}</strong></span>
      <span>Drops: <strong className="font-medium text-[var(--ink)]">{props.drops}</strong></span>
    </div>
  )
}

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span
      aria-hidden
      className={`inline-block h-2.5 w-2.5 rounded-full ${ok ? 'bg-[var(--ok)]' : 'bg-[var(--danger)]'}`}
    />
  )
}

function formatElapsed(s: number): string {
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}
