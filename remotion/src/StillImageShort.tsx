import React from "react";
import {
  AbsoluteFill,
  Audio,
  Easing,
  Img,
  OffthreadVideo,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { StillImageShortFooterCover, StillImageShortOverlay, StillImageShortProps } from "./types";

const GOLD = "#f5c76b";
const WARM = "#fff2c7";
const BLUE = "#07101f";

const clampFrame = (seconds: number, fps: number) => Math.max(1, Math.round(seconds * fps));

const SceneImage: React.FC<{
  src: string;
  durationInFrames: number;
  variant: number;
}> = ({ src, durationInFrames, variant }) => {
  const frame = useCurrentFrame();
  const progress = interpolate(frame, [0, Math.max(1, durationInFrames - 1)], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  const zoomIn = variant % 2 === 0;
  const scale = zoomIn
    ? interpolate(progress, [0, 1], [1.02, 1.11])
    : interpolate(progress, [0, 1], [1.1, 1.02]);
  const panX = interpolate(progress, [0, 1], variant % 3 === 0 ? [-18, 18] : [16, -14]);
  const panY = interpolate(progress, [0, 1], variant % 3 === 1 ? [18, -18] : [-10, 12]);

  return (
    <AbsoluteFill style={{ backgroundColor: "#020409", overflow: "hidden" }}>
      <Img
        src={staticFile(src)}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `translate(${panX}px, ${panY}px) scale(${scale})`,
          filter: "contrast(1.08) saturate(0.92) brightness(0.9)",
        }}
      />
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(to bottom, rgba(0,0,0,0.24), rgba(0,0,0,0) 34%, rgba(0,0,0,0.62) 100%)",
        }}
      />
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(circle at 50% 38%, rgba(91,160,255,0.13), rgba(0,0,0,0) 38%)",
          mixBlendMode: "screen",
        }}
      />
    </AbsoluteFill>
  );
};

const SceneVideo: React.FC<{
  src: string;
  durationInFrames: number;
}> = ({ src, durationInFrames }) => {
  const frame = useCurrentFrame();
  const progress = interpolate(frame, [0, Math.max(1, durationInFrames - 1)], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  const scale = interpolate(progress, [0, 1], [1.01, 1.045]);

  return (
    <AbsoluteFill style={{ backgroundColor: "#020409", overflow: "hidden" }}>
      <OffthreadVideo
        src={staticFile(src)}
        muted
        volume={0}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `scale(${scale})`,
          filter: "contrast(1.08) saturate(0.92) brightness(0.9)",
        }}
      />
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(to bottom, rgba(0,0,0,0.18), rgba(0,0,0,0) 38%, rgba(0,0,0,0.46) 100%)",
        }}
      />
    </AbsoluteFill>
  );
};

const OverlayText: React.FC<{ event: StillImageShortOverlay }> = ({ event }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const duration = clampFrame(event.durationSeconds, fps);
  const opacity = interpolate(frame, [0, 0.25 * fps, duration - 0.25 * fps, duration], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const scale = interpolate(frame, [0, 0.28 * fps, duration], [0.94, 1, 1.02], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  const fontSize =
    event.fontSize ??
    (event.kind === "metric" ? 86 : event.kind === "label" ? 96 : event.kind === "question" ? 118 : 128);
  const top = event.y ?? (event.kind === "label" ? 1240 : 170);
  const color = event.color ?? (event.kind === "metric" || event.kind === "label" ? GOLD : WARM);

  return (
    <AbsoluteFill
      style={{
        alignItems: "center",
        paddingLeft: 54,
        paddingRight: 54,
        paddingTop: top,
        opacity,
        transform: `scale(${scale})`,
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          color,
          fontFamily: '"Leelawadee UI", Tahoma, Arial, sans-serif',
          fontSize,
          fontWeight: 950,
          lineHeight: 1.12,
          textAlign: "center",
          whiteSpace: "pre-line",
          maxWidth: 980,
          textShadow:
            "0 7px 0 rgba(245,166,35,0.82), 0 0 0 #02050c, 0 6px 28px rgba(0,0,0,0.95), 0 0 22px rgba(245,199,107,0.32)",
          WebkitTextStroke: `3px ${BLUE}`,
        }}
      >
        {event.text}
      </div>
    </AbsoluteFill>
  );
};

const ProgressBar: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const width = interpolate(frame, [0, durationInFrames], [0, 100], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ justifyContent: "flex-end" }}>
      <div style={{ width: "100%", height: 7, backgroundColor: "rgba(255,255,255,0.12)" }}>
        <div
          style={{
            width: `${width}%`,
            height: "100%",
            background: `linear-gradient(90deg, #5ec7ff, ${GOLD})`,
          }}
        />
      </div>
    </AbsoluteFill>
  );
};

const FooterCover: React.FC<{ cover?: StillImageShortFooterCover }> = ({ cover }) => {
  if (!cover?.enabled) {
    return null;
  }

  const height = cover.height ?? 230;

  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", pointerEvents: "none" }}>
      <div
        style={{
          height,
          width: "100%",
          padding: "42px 58px 36px",
          boxSizing: "border-box",
          background:
            "linear-gradient(180deg, rgba(2,7,16,0.88), rgba(2,4,9,0.98) 58%, rgba(0,0,0,1) 100%)",
          borderTop: "2px solid rgba(245,199,107,0.72)",
          boxShadow: "0 -22px 54px rgba(0,0,0,0.72), inset 0 1px 0 rgba(255,255,255,0.12)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 32,
        }}
      >
        <div style={{ minWidth: 0 }}>
          <div
            style={{
              color: WARM,
              fontFamily: '"Leelawadee UI", Tahoma, Arial, sans-serif',
              fontSize: 48,
              fontWeight: 950,
              letterSpacing: 0,
              lineHeight: 1,
              textShadow: "0 3px 16px rgba(0,0,0,0.92)",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
              maxWidth: 660,
            }}
          >
            {cover.title ?? "LUNAR TRAIN ORBIT"}
          </div>
          <div
            style={{
              marginTop: 14,
              color: "rgba(255,255,255,0.76)",
              fontFamily: '"Leelawadee UI", Tahoma, Arial, sans-serif',
              fontSize: 26,
              fontWeight: 700,
              letterSpacing: 0,
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
              maxWidth: 690,
            }}
          >
            {cover.subtitle ?? "FALLING AROUND THE MOON"}
          </div>
        </div>
        <div
          style={{
            flex: "0 0 auto",
            minWidth: 238,
            padding: "20px 28px",
            border: "2px solid rgba(94,199,255,0.58)",
            background: "linear-gradient(135deg, rgba(94,199,255,0.16), rgba(245,199,107,0.17))",
            color: GOLD,
            fontFamily: '"Leelawadee UI", Tahoma, Arial, sans-serif',
            fontSize: 38,
            fontWeight: 950,
            textAlign: "center",
            lineHeight: 1,
            boxShadow: "0 0 32px rgba(94,199,255,0.12)",
          }}
        >
          {cover.metric ?? "1.68 km/s"}
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const StillImageShort: React.FC<StillImageShortProps> = ({
  imagePaths,
  assetTypes = [],
  sceneDurations,
  overlayEvents = [],
  footerCover,
  audioPath,
}) => {
  const { fps } = useVideoConfig();
  let cursor = 0;

  return (
    <AbsoluteFill style={{ width: 1080, height: 1920, backgroundColor: "#020409" }}>
      {imagePaths.map((imagePath, index) => {
        const durationInFrames = clampFrame(sceneDurations[index] ?? 3, fps);
        const from = cursor;
        cursor += durationInFrames;
        return (
          <Sequence key={`${imagePath}-${index}`} from={from} durationInFrames={durationInFrames} premountFor={fps}>
            {assetTypes[index] === "video" ? (
              <SceneVideo src={imagePath} durationInFrames={durationInFrames} />
            ) : (
              <SceneImage src={imagePath} durationInFrames={durationInFrames} variant={index} />
            )}
          </Sequence>
        );
      })}
      {overlayEvents.map((event, index) => (
        <Sequence
          key={`${event.text}-${index}`}
          from={Math.round(event.startSeconds * fps)}
          durationInFrames={clampFrame(event.durationSeconds, fps)}
          premountFor={fps}
        >
          <OverlayText event={event} />
        </Sequence>
      ))}
      <FooterCover cover={footerCover} />
      {audioPath ? <Audio src={staticFile(audioPath)} volume={1} /> : null}
      <ProgressBar />
    </AbsoluteFill>
  );
};
