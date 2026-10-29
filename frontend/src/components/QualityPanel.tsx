import type { VitalsPayload } from '../types'

type Props = { vitals: VitalsPayload | null }

export function QualityPanel({ vitals }: Props) {
  const q = vitals?.quality
  const rejects = q?.rejection_reasons ?? []
  const warnings = q?.warnings ?? []

  return (
    <section className="rounded-2xl border border-[var(--line)] bg-[var(--panel)] p-4 shadow-sm">
      <h2 className="brand text-base font-semibold text-[var(--brand-deep)]">Signal quality</h2>
      <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
        <Item label="Category" value={q?.category ?? '—'} />
        <Item label="Score" value={q?.overall_score != null ? q.overall_score.toFixed(2) : '—'} />
        <Item label="Face" value={q?.face_status ?? '—'} />
        <Item label="Motion" value={q?.motion_category ?? '—'} />
        <Item label="Lighting" value={q?.lighting?.status ?? '—'} />
        <Item
          label="Brightness"
          value={q?.lighting?.mean_brightness != null ? q.lighting.mean_brightness.toFixed(0) : '—'}
        />
        <Item
          label="Buffer"
          value={
            typeof q?.pulse?.buffer_frames === 'number'
              ? `${q.pulse.buffer_frames} / 64 frames`
              : '—'
          }
        />
        <Item
          label="Allow new HR"
          value={q?.allow_new_hr_estimate ? 'yes' : 'no'}
        />
      </dl>
      {typeof q?.pulse?.buffer_frames === 'number' && q.pulse.buffer_frames < 64 && (
        <p className="mt-2 text-sm text-[var(--muted)]">
          Warming up… keep your face steady. Heart rate appears after ~64 frames
          ({Math.max(0, 64 - Number(q.pulse.buffer_frames))} remaining).
        </p>
      )}

      <div className="mt-4 space-y-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
          Why a fresh HR may be unavailable
        </h3>
        {rejects.length === 0 && warnings.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">No active rejection reasons.</p>
        ) : (
          <ul className="space-y-1 text-sm">
            {rejects.map((r) => (
              <li key={r} className="rounded-md bg-red-50 px-2 py-1 text-[var(--danger)]">
                Rejected: {r}
              </li>
            ))}
            {warnings
              .filter((w) => !rejects.includes(w))
              .map((w) => (
                <li key={w} className="rounded-md bg-amber-50 px-2 py-1 text-[var(--warn)]">
                  Warning: {w}
                </li>
              ))}
          </ul>
        )}
        {vitals && !vitals.bpm_accepted && vitals.last_accepted_bpm != null && (
          <p className="text-sm text-[var(--stale)]">
            Displaying last accepted HR separately from current estimate. Age:{' '}
            {vitals.last_accepted_bpm_age_s?.toFixed(0) ?? '—'}s
          </p>
        )}
      </div>
    </section>
  )
}

function Item({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-[var(--muted)]">{label}</dt>
      <dd className="font-medium text-[var(--ink)]">{value}</dd>
    </div>
  )
}
