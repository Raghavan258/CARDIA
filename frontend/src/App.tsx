import { useEffect, useState } from 'react'
import { fetchHealth } from './api'
import { CameraPanel } from './components/CameraPanel'
import { DiagnosticCharts } from './components/DiagnosticCharts'
import { QualityPanel } from './components/QualityPanel'
import { StatusBar } from './components/StatusBar'
import { VitalsCards } from './components/VitalsCards'
import { useCamera } from './hooks/useCamera'
import { useMonitorSession } from './hooks/useMonitorSession'

export default function App() {
  const camera = useCamera()
  const monitor = useMonitorSession(camera.videoRef)
  const [healthError, setHealthError] = useState<string | null>(null)

  useEffect(() => {
    fetchHealth()
      .then(() => setHealthError(null))
      .catch((e) => setHealthError(e instanceof Error ? e.message : 'Backend unreachable'))
  }, [])

  const onStart = async () => {
    const ok = camera.status === 'ready' ? true : await camera.start()
    if (!ok) return
    await new Promise((r) => setTimeout(r, 200))
    await monitor.start()
  }

  const onStop = async () => {
    await monitor.stop()
    camera.stop()
  }

  const vitals = monitor.vitals
  const cameraBlocked = camera.status === 'denied' || camera.status === 'error'

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="brand text-3xl font-semibold tracking-tight text-[var(--brand-deep)] sm:text-4xl">
            CARDIA
          </p>
          <p className="mt-1 max-w-xl text-sm text-[var(--muted)]">
            Contactless heart-rate monitoring with explicit signal-quality gating.
            SpO2, blood pressure, and respiration are experimental — not medical advice.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="text-sm text-[var(--muted)]">
            Algorithm{' '}
            <select
              className="ml-1 rounded-lg border border-[var(--line)] bg-white px-2 py-1.5 text-[var(--ink)]"
              value={monitor.algorithm}
              disabled={monitor.running}
              onChange={(e) => monitor.setAlgorithm(e.target.value as 'pos' | 'chrom')}
            >
              <option value="pos">POS</option>
              <option value="chrom">CHROM</option>
            </select>
          </label>
          {!monitor.running ? (
            <button
              type="button"
              onClick={() => void onStart()}
              className="rounded-xl bg-[var(--brand)] px-4 py-2 text-sm font-semibold text-white hover:bg-[var(--brand-deep)]"
            >
              Start monitoring
            </button>
          ) : (
            <button
              type="button"
              onClick={() => void onStop()}
              className="rounded-xl border border-[var(--line)] bg-white px-4 py-2 text-sm font-semibold text-[var(--ink)] hover:bg-slate-50"
            >
              Stop
            </button>
          )}
        </div>
      </header>

      <div className="mb-4 rounded-2xl border border-[var(--line)] bg-[var(--panel)]/80 px-4 py-3 shadow-sm backdrop-blur">
        <StatusBar
          backendOk={healthError ? false : monitor.backendOk}
          conn={monitor.conn}
          state={vitals?.state ?? (monitor.running ? 'initializing' : 'idle')}
          elapsedS={vitals?.session_elapsed_s ?? null}
          latencyMs={monitor.latencyMs}
          effectiveFps={vitals?.effective_fps ?? null}
          drops={monitor.drops}
        />
      </div>

      {(healthError || camera.error || monitor.error || cameraBlocked) && (
        <div className="mb-4 space-y-2" role="alert">
          {healthError && (
            <Alert>
              Backend unreachable ({healthError}). Start it with <code>python -m backend</code>.
            </Alert>
          )}
          {camera.error && <Alert>{camera.error}</Alert>}
          {monitor.error && <Alert>{monitor.error}</Alert>}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        <CameraPanel
          videoRef={camera.videoRef}
          landmarks={vitals?.diagnostics?.landmarks_norm ?? null}
          motionCategory={vitals?.quality?.motion_category}
        />
        <QualityPanel vitals={vitals} />
      </div>

      <div className="mt-4">
        <VitalsCards vitals={vitals} />
      </div>

      <div className="mt-6">
        <DiagnosticCharts
          diagnostics={vitals?.diagnostics ?? null}
          lighting={vitals?.quality?.lighting ?? null}
          latencyMs={monitor.latencyMs}
        />
      </div>

      <footer className="mt-8 border-t border-[var(--line)] pt-4 text-xs text-[var(--muted)]">
        CARDIA is a research prototype. Measurements are not clinical-grade and must not be used
        for diagnosis or treatment decisions.
      </footer>
    </div>
  )
}

function Alert({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-[var(--danger)]">
      {children}
    </div>
  )
}
