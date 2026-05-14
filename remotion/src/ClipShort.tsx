import React from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  OffthreadVideo,
  Sequence,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { ClipShortProps, SrtEntry } from "./types";
import { parseSrt } from "./utils/parseSrt";

const GOLD = "#f5c76b";
const CYAN = "#5ec7ff";

const fitText = (text: string): number => {
  const len = Array.from(text || "").length;
  if (len > 34) return 54;
  if (len > 24) return 62;
  return 72;
};

const containsKeyword = (text: string, keywords: string[] = []) => {
  const lower = text.toLowerCase();
  return keywords.some((keyword) => keyword && lower.includes(keyword.toLowerCase()));
};

const BackgroundVideo: React.FC<Pick<ClipShortProps, "videoPath" | "startAtSeconds">> = ({
  videoPath,
  startAtSeconds,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const startFrom = Math.max(0, Math.floor((startAtSeconds || 0) * fps));
  const zoom = interpolate(frame, [0, durationInFrames], [1.04, 1.14], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "#050507", overflow: "hidden" }}>
      <OffthreadVideo
        src={staticFile(videoPath)}
        startFrom={startFrom}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `scale(${zoom})`,
          filter: "contrast(1.14) saturate(0.92) brightness(0.72)",
        }}
      />
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(circle at 50% 34%, rgba(94,199,255,0.16), rgba(0,0,0,0) 30%), linear-gradient(to bottom, rgba(0,0,0,0.34), rgba(0,0,0,0.1) 32%, rgba(0,0,0,0.88) 100%)",
        }}
      />
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(to right, rgba(0,0,0,0.52), rgba(0,0,0,0.05) 42%, rgba(0,0,0,0.42))",
          mixBlendMode: "multiply",
        }}
      />
    </AbsoluteFill>
  );
};

const Header: React.FC<{ title: string; subtitle?: string }> = ({ title, subtitle }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const opacity = interpolate(frame, [0, 0.35 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const y = interpolate(frame, [0, 0.45 * fps], [-28, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  return (
    <AbsoluteFill
      style={{
        alignItems: "center",
        paddingTop: 94,
        paddingLeft: 58,
        paddingRight: 58,
        opacity,
        transform: `translateY(${y}px)`,
      }}
    >
      <div
        style={{
          color: "#fff",
          fontFamily: "Arial, sans-serif",
          fontSize: 74,
          fontWeight: 950,
          lineHeight: 0.98,
          textAlign: "center",
          textShadow: "0 5px 28px rgba(0,0,0,0.95), 0 0 22px rgba(245,199,107,0.42)",
          WebkitTextStroke: `2px ${GOLD}`,
          maxWidth: 940,
        }}
      >
        {title}
      </div>
      {subtitle ? (
        <div
          style={{
            marginTop: 16,
            color: "#dff5ff",
            fontFamily: "Arial, sans-serif",
            fontSize: 30,
            fontWeight: 800,
            letterSpacing: 1.2,
            textTransform: "uppercase",
            textShadow: "0 3px 12px rgba(0,0,0,0.9)",
          }}
        >
          {subtitle}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

const CaptionCard: React.FC<{
  entry: SrtEntry;
  keywords?: string[];
}> = ({ entry, keywords = [] }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const ms = (frame / fps) * 1000;
  const duration = Math.max(1, entry.endMs - entry.startMs);
  const progress = (ms - entry.startMs) / duration;
  const isHot = containsKeyword(entry.text, keywords);
  const scale = isHot
    ? interpolate(progress, [0, 0.12, 1], [0.92, 1.05, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: Easing.bezier(0.16, 1, 0.3, 1),
      })
    : interpolate(progress, [0, 0.12], [0.96, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: Easing.bezier(0.16, 1, 0.3, 1),
      });
  const opacity =
    progress < 0.08
      ? interpolate(progress, [0, 0.08], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
      : progress > 0.92
        ? interpolate(progress, [0.92, 1], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
        : 1;

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: 188,
        paddingLeft: 58,
        paddingRight: 58,
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          background: isHot ? "rgba(9, 12, 18, 0.86)" : "rgba(5, 7, 11, 0.78)",
          border: `2px solid ${isHot ? GOLD : "rgba(255,255,255,0.18)"}`,
          boxShadow: isHot
            ? "0 0 42px rgba(245,199,107,0.22), 0 20px 70px rgba(0,0,0,0.72)"
            : "0 18px 62px rgba(0,0,0,0.72)",
          borderRadius: 8,
          padding: "22px 30px 26px",
          transform: `scale(${scale})`,
          opacity,
          maxWidth: 940,
        }}
      >
        <div
          style={{
            color: isHot ? "#fff6d8" : "#ffffff",
            fontFamily: "Arial, sans-serif",
            fontSize: fitText(entry.text),
            fontWeight: 950,
            lineHeight: 1.13,
            textAlign: "center",
            textShadow: "0 4px 16px rgba(0,0,0,0.95)",
          }}
        >
          {entry.text}
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Captions: React.FC<{ entries: SrtEntry[]; keywords?: string[] }> = ({ entries, keywords }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentMs = (frame / fps) * 1000;
  const active = entries.find((entry) => currentMs >= entry.startMs && currentMs < entry.endMs);
  if (!active) return null;
  return <CaptionCard entry={active} keywords={keywords} />;
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
      <div style={{ width: "100%", height: 8, backgroundColor: "rgba(255,255,255,0.12)" }}>
        <div
          style={{
            width: `${width}%`,
            height: "100%",
            background: `linear-gradient(90deg, ${CYAN}, ${GOLD})`,
          }}
        />
      </div>
    </AbsoluteFill>
  );
};

const ColdOpenStamp: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const opacity = interpolate(frame, [0.5 * fps, 1.0 * fps, 4.2 * fps, 4.8 * fps], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <Sequence from={0} durationInFrames={5 * fps} premountFor={fps}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity }}>
        <div
          style={{
            color: GOLD,
            fontFamily: "Arial, sans-serif",
            fontSize: 34,
            fontWeight: 900,
            letterSpacing: 4,
            padding: "12px 22px",
            border: `2px solid ${GOLD}`,
            borderRadius: 4,
            background: "rgba(0,0,0,0.62)",
            transform: "rotate(-2deg)",
          }}
        >
          BILLION-DOLLAR ANTI-AGING RACE
        </div>
      </AbsoluteFill>
    </Sequence>
  );
};

export const ClipShort: React.FC<ClipShortProps> = (props) => {
  const entries = parseSrt(props.srtContent || "");

  return (
    <AbsoluteFill style={{ width: 1080, height: 1920, backgroundColor: "#020204" }}>
      <BackgroundVideo videoPath={props.videoPath} startAtSeconds={props.startAtSeconds || 0} />
      <Header title={props.title} subtitle={props.subtitle} />
      <ColdOpenStamp />
      <Captions entries={entries} keywords={props.keywordHighlights} />
      <ProgressBar />
    </AbsoluteFill>
  );
};
