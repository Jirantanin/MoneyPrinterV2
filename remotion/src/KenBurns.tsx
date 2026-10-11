import React from "react";
import { AbsoluteFill, staticFile, useCurrentFrame, interpolate } from "remotion";

// ─── Shared Ken Burns constants ──────────────────────────────────────────────
export const TRANSITION_FRAMES = 18; // ~0.6s at 30fps / ~0.7s at 25fps
export const KB_CYCLE = ['zoom-in', 'zoom-out', 'pan-left', 'pan-right'] as const;
export const SLIDE_DIRS = ['from-left', 'from-right', 'from-top', 'from-bottom'] as const;
export type KenBurnsVariant = typeof KB_CYCLE[number];

// ─── KenBurnsFrame component ─────────────────────────────────────────────────
export const KenBurnsFrame: React.FC<{
  imgPath: string;
  variant: KenBurnsVariant;
  durationInFrames: number;
  profile?: 'default' | 'documentary-readable';
  fit?: 'cover' | 'contain';
}> = ({ imgPath, variant, durationInFrames, profile = 'default', fit = 'cover' }) => {
  const frame = useCurrentFrame();
  const progress = frame / Math.max(durationInFrames, 1);
  const readableMotion = profile === 'documentary-readable';
  const zoomMax = readableMotion ? 1.045 : 1.2;

  let transform = '';
  switch (variant) {
    case 'zoom-in':
      transform = `scale(${interpolate(progress, [0, 1], [1.0, zoomMax], { extrapolateRight: 'clamp' })})`;
      break;
    case 'zoom-out':
      transform = `scale(${interpolate(progress, [0, 1], [zoomMax, 1.0], { extrapolateRight: 'clamp' })})`;
      break;
    case 'pan-left':
      transform = `scale(1.15) translateX(${interpolate(progress, [0, 1], [3, -8], { extrapolateRight: 'clamp' })}%)`;
      break;
    case 'pan-right':
      transform = `scale(1.15) translateX(${interpolate(progress, [0, 1], [-3, 8], { extrapolateRight: 'clamp' })}%)`;
      break;
  }

  return (
    <AbsoluteFill style={{ backgroundColor: fit === 'contain' ? '#050910' : undefined }}>
      <img
        src={staticFile(imgPath)}
        style={{
          width: '100%',
          height: '100%',
          objectFit: fit,
          transform: fit === 'contain' ? 'none' : transform,
          transformOrigin: 'center center',
        }}
      />
    </AbsoluteFill>
  );
};
