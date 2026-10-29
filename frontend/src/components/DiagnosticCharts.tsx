import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { Diagnostics, QualityPayload } from '../types'

type Props = {
  diagnostics: Diagnostics | null
  lighting: QualityPayload['lighting'] | null
  latencyMs: number | null
}

export function DiagnosticCharts({ diagnostics, lighting, latencyMs }: Props) {
  const rgb = (diagnostics?.rgb.t || []).map((t, i) => ({
    t: Number(t.toFixed(2)),
    r: diagnostics!.rgb.r[i],
    g: diagnostics!.rgb.g[i],
    b: diagnostics!.rgb.b[i],
  }))
  const pulse = (diagnostics?.pulse.t || []).map((t, i) => ({
    t: Number(t.toFixed(2)),
    y: diagnostics!.pulse.y[i],
  }))
  const spectrum = (diagnostics?.spectrum.freq_hz || []).map((f, i) => ({
    hz: Number(f.toFixed(2)),
    psd: diagnostics!.spectrum.psd[i],
  }))
  const hr = (diagnostics?.hr_series || []).map((p) => ({
    t: Number(p.t.toFixed(1)),
    bpm: p.bpm,
  }))
  const motion = (diagnostics?.motion_history || []).map((p) => ({
    t: Number(p.t.toFixed(1)),
    score: p.score,
  }))

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <h2 className="brand text-base font-semibold text-[var(--brand-deep)]">Diagnostics</h2>
        <p className="text-xs text-[var(--muted)]">
          Charts use measured backend traces only · processing latency{' '}
          {latencyMs != null ? `${latencyMs.toFixed(0)} ms` : '—'}
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Raw RGB (ROI means)" empty={!rgb.length}>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={rgb}>
              <CartesianGrid stroke="#e5ecef" strokeDasharray="3 3" />
              <XAxis dataKey="t" tick={{ fontSize: 11 }} label={{ value: 't (s)', position: 'insideBottom', offset: -2, fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Line type="monotone" dataKey="r" stroke="#c23b22" dot={false} strokeWidth={1.5} isAnimationActive={false} />
              <Line type="monotone" dataKey="g" stroke="#1f7a4d" dot={false} strokeWidth={1.5} isAnimationActive={false} />
              <Line type="monotone" dataKey="b" stroke="#1d4f91" dot={false} strokeWidth={1.5} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Extracted pulse" empty={!pulse.length}>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={pulse}>
              <CartesianGrid stroke="#e5ecef" strokeDasharray="3 3" />
              <XAxis dataKey="t" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Line type="monotone" dataKey="y" stroke="#0f6b7a" dot={false} strokeWidth={1.75} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Frequency spectrum" empty={!spectrum.length}>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={spectrum}>
              <CartesianGrid stroke="#e5ecef" strokeDasharray="3 3" />
              <XAxis dataKey="hz" tick={{ fontSize: 11 }} label={{ value: 'Hz', position: 'insideBottom', offset: -2, fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Area type="monotone" dataKey="psd" stroke="#0a4550" fill="#b7dce2" isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Accepted heart-rate history" empty={!hr.length}>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={hr}>
              <CartesianGrid stroke="#e5ecef" strokeDasharray="3 3" />
              <XAxis dataKey="t" tick={{ fontSize: 11 }} />
              <YAxis domain={['auto', 'auto']} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Line type="monotone" dataKey="bpm" stroke="#9a5b12" dot={false} strokeWidth={1.75} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Motion score over time" empty={!motion.length}>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={motion}>
              <CartesianGrid stroke="#e5ecef" strokeDasharray="3 3" />
              <XAxis dataKey="t" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Line type="monotone" dataKey="score" stroke="#5b6d76" dot={false} strokeWidth={1.5} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Lighting statistics" empty={false}>
          <ul className="grid grid-cols-2 gap-3 p-2 text-sm">
            <Stat label="Mean brightness" value={fmt(lighting?.mean_brightness)} />
            <Stat label="Median brightness" value={fmt(lighting?.median_brightness)} />
            <Stat label="Underexposed frac" value={pct(lighting?.underexposed_fraction)} />
            <Stat label="Overexposed frac" value={pct(lighting?.overexposed_fraction)} />
            <Stat label="Brightness Δ" value={fmt(lighting?.brightness_delta)} />
            <Stat label="ROI spread" value={fmt(lighting?.roi_brightness_spread)} />
            <Stat label="Status" value={lighting?.status ?? '—'} />
          </ul>
        </ChartCard>
      </div>
    </section>
  )
}

function ChartCard({
  title,
  empty,
  children,
}: {
  title: string
  empty: boolean
  children: React.ReactNode
}) {
  return (
    <div className="rounded-2xl border border-[var(--line)] bg-[var(--panel)] p-3 shadow-sm">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">{title}</h3>
      {empty ? (
        <p className="flex h-[180px] items-center justify-center text-sm text-[var(--muted)]">
          Waiting for measured data…
        </p>
      ) : (
        children
      )}
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <li>
      <div className="text-xs text-[var(--muted)]">{label}</div>
      <div className="font-medium">{value}</div>
    </li>
  )
}

function fmt(v: number | null | undefined): string {
  return v == null ? '—' : v.toFixed(1)
}

function pct(v: number | null | undefined): string {
  return v == null ? '—' : `${(v * 100).toFixed(1)}%`
}
