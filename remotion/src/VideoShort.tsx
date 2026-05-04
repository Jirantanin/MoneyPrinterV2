import React from "react";
import {
  AbsoluteFill,
  Audio,
  staticFile,
  useVideoConfig,
  useCurrentFrame,
  interpolate,
} from "remotion";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { slide } from "@remotion/transitions/slide";
import { VideoProps, SrtEntry } from "./types";
import { CategoryPreset, getPreset } from "./presets";
import { parseSrt } from "./utils/parseSrt";
import { KenBurnsFrame, KB_CYCLE, SLIDE_DIRS, TRANSITION_FRAMES } from "./KenBurns";

const ImageSlideshow: React.FC<Pick<VideoProps, 'imagePaths' | 'durationInSeconds'>> = ({
  imagePaths,
}) => {
  const { durationInFrames: totalFrames } = useVideoConfig();

  if (imagePaths.length === 0) {
    return <AbsoluteFill style={{ backgroundColor: '#111' }} />;
  }

  const n = imagePaths.length;
  // Guard: ensure transition frames don't exceed half of per-image raw duration
  const perImageRaw = totalFrames / n;
  const tf = n > 1 ? Math.min(TRANSITION_FRAMES, Math.floor(perImageRaw / 2)) : 0;

  // Duration compensation: TransitionSeries shortens total by (n-1)*tf
  // so pad each image's duration to absorb the overlap
  const perImage = n > 1
    ? Math.round((totalFrames + (n - 1) * tf) / n)
    : totalFrames;

  return (
    <TransitionSeries>
      {imagePaths.map((imgPath, i) => (
        <React.Fragment key={i}>
          <TransitionSeries.Sequence durationInFrames={perImage}>
            <KenBurnsFrame
              imgPath={imgPath}
              variant={KB_CYCLE[i % KB_CYCLE.length]}
              durationInFrames={perImage}
            />
          </TransitionSeries.Sequence>
          {i < n - 1 && (
            <TransitionSeries.Transition
              presentation={slide({ direction: SLIDE_DIRS[i % SLIDE_DIRS.length] })}
              timing={linearTiming({ durationInFrames: tf })}
            />
          )}
        </React.Fragment>
      ))}
    </TransitionSeries>
  );
};

// ─── Layer 2: Dark gradient overlay ──────────────────────────────────────────
const GradientOverlay: React.FC = () => (
  <AbsoluteFill
    style={{
      background:
        "linear-gradient(to bottom, transparent 40%, rgba(0,0,0,0.80) 100%)",
      pointerEvents: "none",
    }}
  />
);

// ─── Layer 3: Category badge ──────────────────────────────────────────────────
const CategoryBadge: React.FC<{ preset: CategoryPreset }> = ({ preset }) => (
  <AbsoluteFill
    style={{
      top: 150,
      left: 40,
      bottom: "auto",
      right: "auto",
      height: "auto",
      width: "auto",
    }}
  >
    <div
      style={{
        backgroundColor: preset.badgeColor,
        color: "#fff",
        fontFamily: "sans-serif",
        fontWeight: 800,
        fontSize: 36,
        padding: "10px 24px",
        borderRadius: 6,
        letterSpacing: 1,
        display: "inline-block",
      }}
    >
      {preset.badgeLabel}
    </div>
  </AbsoluteFill>
);

// ─── Layer 4: Subtitle layer ──────────────────────────────────────────────────
const SubtitleLayer: React.FC<{
  frame: number;
  fps: number;
  entries: SrtEntry[];
  preset: CategoryPreset;
}> = ({ frame, fps, entries, preset }) => {
  const currentMs = (frame / fps) * 1000;
  const active = entries.find((e) => currentMs >= e.startMs && currentMs < e.endMs);

  if (!active) return null;

  const window = active.endMs - active.startMs;
  const localProgress = window > 0 ? (currentMs - active.startMs) / window : 0;

  let opacity = 1;
  let translateY = 0;
  let scale = 1;

  if (preset.subtitleAnimation === "fade") {
    opacity =
      localProgress < 0.1
        ? interpolate(localProgress, [0, 0.1], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
        : localProgress > 0.9
        ? interpolate(localProgress, [0.9, 1], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
        : 1;
  } else if (preset.subtitleAnimation === "slide_up") {
    translateY =
      localProgress < 0.15
        ? interpolate(localProgress, [0, 0.15], [30, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
        : 0;
    opacity = localProgress < 0.1 ? interpolate(localProgress, [0, 0.1], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 1;
  } else if (preset.subtitleAnimation === "pop") {
    scale =
      localProgress < 0.1
        ? interpolate(localProgress, [0, 0.1], [0.7, 1.05], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
        : localProgress < 0.15
        ? interpolate(localProgress, [0.1, 0.15], [1.05, 1.0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
        : 1;
  }

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: 170,
        paddingLeft: 40,
        paddingRight: 40,
      }}
    >
      <div
        style={{
          color: "#fff",
          fontSize: 64,
          fontFamily: "sans-serif",
          fontWeight: 800,
          textAlign: "center",
          lineHeight: 1.25,
          textShadow: `0 2px 12px rgba(0,0,0,0.9), 0 0 4px ${preset.accentColor}`,
          opacity,
          transform: `translateY(${translateY}px) scale(${scale})`,
        }}
      >
        {active.text}
      </div>
    </AbsoluteFill>
  );
};

// ─── Breaking news ticker ─────────────────────────────────────────────────────
const BreakingNewsTicker: React.FC<{ topic: string; frame: number; totalFrames: number }> = ({
  topic,
  frame,
  totalFrames,
}) => {
  const xPos = interpolate(frame, [0, totalFrames], [1080, -topic.length * 28], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        top: "auto",
        bottom: 0,
        height: 64,
        backgroundColor: "#cc0000",
        overflow: "hidden",
        alignItems: "center",
      }}
    >
      <div
        style={{
          position: "absolute",
          left: xPos,
          whiteSpace: "nowrap",
          color: "#fff",
          fontFamily: "sans-serif",
          fontWeight: 900,
          fontSize: 36,
          letterSpacing: 2,
        }}
      >
        🔴 {topic.toUpperCase()} 🔴 {topic.toUpperCase()}
      </div>
    </AbsoluteFill>
  );
};

// ─── Root composition ─────────────────────────────────────────────────────────
export const VideoShort: React.FC<VideoProps> = (props) => {
  const { fps, durationInFrames } = useVideoConfig();
  const frame = useCurrentFrame();
  const preset = getPreset(props.category);
  const srtEntries = parseSrt(props.srtContent);

  return (
    <AbsoluteFill style={{ backgroundColor: "#000", width: 1080, height: 1920 }}>
      <ImageSlideshow imagePaths={props.imagePaths} durationInSeconds={props.durationInSeconds} />
      <GradientOverlay />
      {preset.badgeLabel && <CategoryBadge preset={preset} />}
      {preset.overlayStyle === "breaking_news_ticker" && (
        <BreakingNewsTicker topic={props.topic} frame={frame} totalFrames={durationInFrames} />
      )}
      <SubtitleLayer frame={frame} fps={fps} entries={srtEntries} preset={preset} />
      {props.audioPath && <Audio src={staticFile(props.audioPath)} />}
      {props.bgmPath && <Audio src={staticFile(props.bgmPath)} volume={0.08} loop />}
    </AbsoluteFill>
  );
};
