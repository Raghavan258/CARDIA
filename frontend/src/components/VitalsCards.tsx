import type { VitalsPayload } from '../types'

type Props = { vitals: VitalsPayload | null }

export function VitalsCards({ vitals }: Props) {
  const accepted = vitals?.bpm_accepted && vitals.bpm != null
  const stale =
    !accepted && vitals?.last_accepted_bpm != null
      ? vitals.last_accepted_bpm
      : null
  const age = vitals?.last_accepted_bpm_age_s

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Card
        title="Heart Rate"
        value={accepted ? Math.round(vitals!.bpm!) : stale != null ? Math.round(stale) : '—'}
        unit="bpm"
        footnote={
          accepted
            ? 'Accepted reading'
            : stale != null
              ? `Last accepted${age != null ? ` · ${age.toFixed(0)}s ago` : ''} (not current)`
              : 'No accepted reading yet'
        }
        tone={accepted ? 'ok' : stale != null ? 'stale' : 'neutral'}
        primary
      />
      <Card
        title="SpO2"
        value={vitals?.spo2 != null ? Math.round(vitals.spo2) : '—'}
        unit="%"
        footnote="Experimental estimate"
        tone="warn"
      />
      <Card
        title="Blood Pressure"
        value={
          vitals?.bp_sys != null && vitals?.bp_dia != null
            ? `${Math.round(vitals.bp_sys)}/${Math.round(vitals.bp_dia)}`
            : '—'
        }
        unit="mmHg"
        footnote="Experimental estimate"
        tone="warn"
      />
      <Card
        title="Respiration"
        value={vitals?.resp_rate != null ? Math.round(vitals.resp_rate) : '—'}
        unit="/min"
        footnote="Experimental estimate"
        tone="warn"
      />
    </div>
  )
}

function Card(props: {
  title: string
  value: string | number
  unit: string
  footnote: string
  tone: 'ok' | 'stale' | 'warn' | 'neutral'
  primary?: boolean
}) {
  const toneClass =
    props.tone === 'ok'
      ? 'border-[var(--ok)]/40'
      : props.tone === 'stale'
        ? 'border-[var(--stale)]/50'
        : props.tone === 'warn'
          ? 'border-[var(--warn)]/35'
          : 'border-[var(--line)]'

  return (
    <article className={`rounded-2xl border bg-[var(--panel)] p-4 shadow-sm ${toneClass}`}>
      <div className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
        {props.title}
        {props.primary ? '' : ' · experimental'}
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <span className={`brand text-3xl font-semibold ${props.tone === 'stale' ? 'text-[var(--stale)]' : 'text-[var(--ink)]'}`}>
          {props.value}
        </span>
        <span className="text-sm text-[var(--muted)]">{props.unit}</span>
      </div>
      <p className="mt-2 text-xs text-[var(--muted)]">{props.footnote}</p>
    </article>
  )
}
