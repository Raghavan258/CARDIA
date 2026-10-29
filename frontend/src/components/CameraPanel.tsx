import type { RefObject } from 'react'
import type { Diagnostics } from '../types'

type Props = {
  videoRef: RefObject<HTMLVideoElement | null>
  landmarks: Diagnostics['landmarks_norm']
  motionCategory?: string
}

/** Live camera preview with optional landmark overlay (normalized coords). */
export function CameraPanel({ videoRef, landmarks, motionCategory }: Props) {
  return (
    <div className="relative overflow-hidden rounded-2xl bg-[#0a4550] shadow-sm ring-1 ring-[var(--line)]">
      <video
        ref={videoRef}
        className="aspect-[4/3] w-full object-cover"
        playsInline
        muted
        autoPlay
      />
      <svg className="pointer-events-none absolute inset-0 h-full w-full" viewBox="0 0 1 1" preserveAspectRatio="none">
        {landmarks?.map((p, i) => (
          <circle key={i} cx={p.x} cy={p.y} r={0.004} fill="#7fd4df" opacity={0.85} />
        ))}
      </svg>
      {motionCategory && motionCategory !== 'low' && (
        <div className="absolute bottom-3 left-3 rounded-md bg-black/55 px-2 py-1 text-xs text-white">
          Motion: {motionCategory}
        </div>
      )}
    </div>
  )
}
