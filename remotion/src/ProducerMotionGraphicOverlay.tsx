import React from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { PRODUCER_FONT_FAMILY } from "./producerFonts";
import { ProducerMotionGraphic } from "./types";

const OUTLINE = "#20272b";
const CREAM = "#f5ead2";
const RED = "#e85a62";
const CYAN = "#55c2d2";
const YELLOW = "#e9b94c";
const GREEN = "#63c9bd";
const BLUE = "#86a4e0";
const PINK = "#dfb3bf";
const MINT = "#b8d9ce";
const SKY = "#b6d5e4";
const LAVENDER = "#c9bee3";
const PEACH = "#dfbea6";
const EASE_OUT = Easing.bezier(0.16, 1, 0.3, 1);

const backgrounds: Record<string, string> = {
  bar_share: PINK,
  orbit_slots: SKY,
  spectrum: MINT,
  queue: LAVENDER,
};

const accentFor = (kind: string, metric?: string) => {
  if (kind === "queue") return YELLOW;
  if (kind === "spectrum") return CYAN;
  if (kind === "orbit_slots" && metric !== "LEO") return PEACH;
  return RED;
};

const PopText: React.FC<{
  children: React.ReactNode;
  x?: number;
  y?: number;
  align?: "left" | "center" | "right";
  size: number;
  color?: string;
  weight?: number;
}> = ({ children, x, y, align = "left", size, color = OUTLINE, weight = 800 }) => (
  <div
    style={{
      position: x === undefined && y === undefined ? "relative" : "absolute",
      left: x,
      top: y,
      width: align === "center" ? "100%" : undefined,
      textAlign: align,
      color,
      fontFamily: PRODUCER_FONT_FAMILY,
      fontSize: size,
      lineHeight: 1.08,
      fontWeight: weight,
      textShadow: "0 2px 0 rgba(255,255,255,0.46)",
      overflowWrap: "anywhere",
    }}
  >
    {children}
  </div>
);

const Background: React.FC<{ color: string; progress: number }> = ({ color, progress }) => (
  <AbsoluteFill
    style={{
      opacity: progress,
      background: color,
    }}
  >
    <div
      style={{
        position: "absolute",
        inset: 74,
        background: "rgba(255,255,255,0.1)",
        border: `6px solid ${OUTLINE}`,
        boxShadow: "0 16px 0 rgba(32,39,43,0.18)",
      }}
    />
  </AbsoluteFill>
);

const CaptionPlate: React.FC<{ spec: ProducerMotionGraphic; progress: number }> = ({
  spec,
  progress,
}) => {
  const accent = accentFor(spec.kind, spec.metric);
  return (
    <div
      style={{
        position: "absolute",
        left: 210,
        right: 210,
        bottom: 98,
        minHeight: 156,
        padding: "24px 34px",
        background: CREAM,
        border: `6px solid ${OUTLINE}`,
        boxShadow: "0 12px 0 rgba(32,39,43,0.24)",
        display: "grid",
        gridTemplateColumns: "1fr auto",
        gap: 28,
        alignItems: "center",
        opacity: progress,
        transform: `translateY(${(1 - progress) * 22}px)`,
        fontFamily: PRODUCER_FONT_FAMILY,
      }}
    >
      <div>
        <div
          style={{
            color: OUTLINE,
            fontSize: 42,
            lineHeight: 1.08,
            fontWeight: 860,
            marginBottom: 8,
          }}
        >
          {spec.title}
        </div>
        <div
          style={{
            color: "#3d464b",
            fontSize: 25,
            lineHeight: 1.18,
            fontWeight: 650,
          }}
        >
          {spec.subtitle}
        </div>
      </div>
      <div
        style={{
          minWidth: 310,
          padding: "14px 22px",
          background: accent,
          border: `5px solid ${OUTLINE}`,
          color: OUTLINE,
          fontSize: spec.metric && spec.metric.length > 8 ? 58 : 72,
          lineHeight: 0.96,
          fontWeight: 900,
          textAlign: "center",
        }}
      >
        {spec.metric}
      </div>
    </div>
  );
};

const RocketAndTower: React.FC<{ progress: number; frame: number }> = ({ progress, frame }) => {
  const lift = interpolate(progress, [0, 1], [36, 0]);
  const flame = 1 + Math.sin(frame / 4) * 0.08;
  return (
    <svg
      viewBox="0 0 900 560"
      style={{
        position: "absolute",
        left: 500,
        top: 124,
        width: 1080,
        height: 672,
        transform: `translateY(${lift}px) scale(${0.94 + progress * 0.06})`,
        opacity: progress,
      }}
    >
      <rect x="230" y="430" width="430" height="34" fill={YELLOW} stroke={OUTLINE} strokeWidth="9" />
      <rect x="230" y="410" width="430" height="24" fill="#47c5ea" stroke={OUTLINE} strokeWidth="9" />
      <rect x="280" y="164" width="178" height="250" rx="10" fill="#f5f5f5" stroke={OUTLINE} strokeWidth="9" />
      {[0, 1, 2, 3].map((row) => (
        <line key={`r${row}`} x1="280" x2="458" y1={224 + row * 56} y2={224 + row * 56} stroke={OUTLINE} strokeWidth="7" />
      ))}
      {[0, 1].map((col) => (
        <line key={`c${col}`} x1={338 + col * 60} x2={338 + col * 60} y1="164" y2="414" stroke={OUTLINE} strokeWidth="7" />
      ))}
      <rect x="280" y="154" width="178" height="22" rx="8" fill={CYAN} stroke={OUTLINE} strokeWidth="8" />
      <path d="M348 154 C348 132 392 132 392 154" fill="none" stroke={OUTLINE} strokeWidth="8" />
      <g transform={`translate(0 ${-lift * 0.35})`}>
        <path d="M578 86 C514 126 500 230 502 286 L654 286 C656 230 642 126 578 86Z" fill="#ffffff" stroke={OUTLINE} strokeWidth="9" />
        <path d="M578 86 C608 104 630 140 642 180 L514 180 C526 140 548 104 578 86Z" fill={RED} stroke={OUTLINE} strokeWidth="9" />
        <path d="M502 226 L458 282 C450 292 456 314 470 310 L508 290Z" fill={RED} stroke={OUTLINE} strokeWidth="9" />
        <path d="M654 226 L698 282 C706 292 700 314 686 310 L648 290Z" fill={RED} stroke={OUTLINE} strokeWidth="9" />
        <circle cx="578" cy="178" r="18" fill={CYAN} stroke={OUTLINE} strokeWidth="8" />
        <circle cx="578" cy="226" r="34" fill={CYAN} stroke={OUTLINE} strokeWidth="8" />
        <rect x="526" y="286" width="104" height="42" fill={RED} stroke={OUTLINE} strokeWidth="9" />
        <path d="M542 328 L614 328 L598 374 L558 374Z" fill="#f7f7f7" stroke={OUTLINE} strokeWidth="9" />
        <path
          d={`M558 372 C562 ${410 * flame} 594 ${410 * flame} 598 372 C622 390 608 438 578 454 C548 438 534 390 558 372Z`}
          fill="#ff8a00"
          stroke={OUTLINE}
          strokeWidth="8"
        />
      </g>
      <path d="M326 422 C322 382 382 374 398 408 C426 370 490 390 488 430Z" fill="#ffffff" stroke={OUTLINE} strokeWidth="8" />
      <path d="M500 432 C492 388 558 378 578 414 C608 378 674 392 660 436Z" fill="#ffffff" stroke={OUTLINE} strokeWidth="8" />
    </svg>
  );
};

const MiniBars: React.FC<{ spec: ProducerMotionGraphic; progress: number }> = ({ spec, progress }) => {
  const bars = (spec.bars ?? []).slice(0, 2);
  const maxBar = Math.max(1, ...bars.map((bar) => Number(bar.max ?? bar.value ?? 0)));
  return (
    <div
      style={{
        position: "absolute",
        left: 148,
        top: 352,
        width: 440,
        padding: 24,
        background: CREAM,
        border: `5px solid ${OUTLINE}`,
        boxShadow: "8px 8px 0 rgba(32,39,43,0.2)",
        opacity: progress,
        fontFamily: PRODUCER_FONT_FAMILY,
      }}
    >
      {bars.map((bar, index) => {
        const color = bar.color || [YELLOW, GREEN][index % 2];
        const value = Number(bar.value || 0);
        const ratio = Math.max(0, Math.min(1, value / maxBar)) * progress;
        return (
          <div key={`${bar.label}-${index}`} style={{ marginBottom: index === 0 ? 24 : 0 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
              <span style={{ color: OUTLINE, fontSize: 25, fontWeight: 800 }}>{bar.label}</span>
              <span style={{ color: OUTLINE, fontSize: 28, fontWeight: 900 }}>{Math.round(value * progress)}</span>
            </div>
            <div style={{ height: 20, border: `4px solid ${OUTLINE}`, background: "#fff" }}>
              <div style={{ width: `${ratio * 100}%`, height: "100%", background: color }} />
            </div>
          </div>
        );
      })}
    </div>
  );
};

const OrbitCartoon: React.FC<{ progress: number; frame: number }> = ({ progress, frame }) => (
  <svg
    viewBox="0 0 900 560"
    style={{
      position: "absolute",
      left: 510,
      top: 142,
      width: 900,
      height: 560,
      opacity: progress,
      transform: `scale(${0.92 + progress * 0.08})`,
    }}
  >
    <circle cx="450" cy="286" r="96" fill="#43a6d9" stroke={OUTLINE} strokeWidth="10" />
    <path d="M382 260 C410 210 492 208 524 258 C492 238 444 256 430 294 C414 286 398 276 382 260Z" fill="#72d6a3" stroke={OUTLINE} strokeWidth="7" />
    <path d="M410 346 C452 370 510 350 536 312 C492 324 456 314 430 286 C420 308 414 328 410 346Z" fill="#72d6a3" stroke={OUTLINE} strokeWidth="7" />
    {[0, 1, 2].map((ring) => {
      const rx = 170 + ring * 88;
      const ry = 72 + ring * 34;
      const angle = ((frame * (0.6 + ring * 0.2) + ring * 70) * Math.PI) / 180;
      const x = 450 + Math.cos(angle) * rx;
      const y = 286 + Math.sin(angle) * ry;
      return (
        <g key={ring}>
          <ellipse cx="450" cy="286" rx={rx} ry={ry} fill="none" stroke={OUTLINE} strokeWidth="6" opacity="0.28" />
          <g transform={`translate(${x - 34} ${y - 18}) rotate(${ring * 10})`}>
            <rect x="0" y="7" width="68" height="22" rx="4" fill={YELLOW} stroke={OUTLINE} strokeWidth="6" />
            <rect x="25" y="0" width="18" height="36" rx="3" fill={CYAN} stroke={OUTLINE} strokeWidth="5" />
          </g>
        </g>
      );
    })}
  </svg>
);

const SpectrumCartoon: React.FC<{ progress: number; frame: number }> = ({ progress, frame }) => (
  <svg
    viewBox="0 0 900 560"
    style={{
      position: "absolute",
      left: 510,
      top: 142,
      width: 900,
      height: 560,
      opacity: progress,
      transform: `scale(${0.92 + progress * 0.08})`,
    }}
  >
    <rect x="258" y="382" width="384" height="42" fill={YELLOW} stroke={OUTLINE} strokeWidth="9" />
    <path d="M450 382 L360 164 L540 164Z" fill="#f7f7f7" stroke={OUTLINE} strokeWidth="9" />
    <path d="M372 188 C410 226 490 226 528 188" fill="none" stroke={OUTLINE} strokeWidth="9" />
    <circle cx="450" cy="216" r="32" fill={CYAN} stroke={OUTLINE} strokeWidth="8" />
    {[0, 1, 2].map((i) => {
      const pulse = 1 + Math.sin(frame / 10 + i) * 0.08;
      return (
        <path
          key={i}
          d={`M${310 - i * 38} ${184 - i * 28} C${372 - i * 22} ${118 - i * 34} ${528 + i * 22} ${118 - i * 34} ${590 + i * 38} ${184 - i * 28}`}
          fill="none"
          stroke={i % 2 === 0 ? RED : BLUE}
          strokeWidth={7 * pulse}
          strokeLinecap="round"
          opacity={0.75 - i * 0.14}
        />
      );
    })}
    {[0, 1, 2, 3, 4].map((bar) => (
      <rect
        key={bar}
        x={624 + bar * 34}
        y={364 - bar * 26}
        width="22"
        height={60 + bar * 26}
        fill={[YELLOW, GREEN, RED, BLUE, CYAN][bar]}
        stroke={OUTLINE}
        strokeWidth="5"
      />
    ))}
  </svg>
);

const QueueCartoon: React.FC<{ progress: number }> = ({ progress }) => (
  <svg
    viewBox="0 0 900 560"
    style={{
      position: "absolute",
      left: 510,
      top: 142,
      width: 900,
      height: 560,
      opacity: progress,
      transform: `scale(${0.92 + progress * 0.08})`,
    }}
  >
    <rect x="220" y="386" width="460" height="36" fill={YELLOW} stroke={OUTLINE} strokeWidth="9" />
    {Array.from({ length: 12 }).map((_, index) => {
      const col = index % 4;
      const row = Math.floor(index / 4);
      const fill = index / 12 < progress * 0.72;
      return (
        <rect
          key={index}
          x={268 + col * 94}
          y={138 + row * 84}
          width="70"
          height="58"
          rx="8"
          fill={fill ? [YELLOW, GREEN, RED, BLUE][index % 4] : "#fff6df"}
          stroke={OUTLINE}
          strokeWidth="7"
        />
      );
    })}
    <path d="M650 162 L696 162 L696 350 L650 350Z" fill="#f7f7f7" stroke={OUTLINE} strokeWidth="8" />
    <path d="M650 162 L696 162 L686 132 L660 132Z" fill={CYAN} stroke={OUTLINE} strokeWidth="8" />
    <circle cx="673" cy="380" r="28" fill={RED} stroke={OUTLINE} strokeWidth="8" />
  </svg>
);

const Illustration: React.FC<{ spec: ProducerMotionGraphic; progress: number; frame: number }> = ({
  spec,
  progress,
  frame,
}) => {
  if (spec.kind === "orbit_slots") {
    return <OrbitCartoon progress={progress} frame={frame} />;
  }
  if (spec.kind === "spectrum") {
    return <SpectrumCartoon progress={progress} frame={frame} />;
  }
  if (spec.kind === "queue") {
    return <QueueCartoon progress={progress} />;
  }
  return (
    <>
      <RocketAndTower progress={progress} frame={frame} />
      <MiniBars spec={spec} progress={progress} />
    </>
  );
};

const TitleBlock: React.FC<{ spec: ProducerMotionGraphic; progress: number }> = ({
  spec,
  progress,
}) => {
  const accent = accentFor(spec.kind, spec.metric);
  return (
    <div
      style={{
        position: "absolute",
        left: 148,
        top: 112,
        width: 680,
        opacity: progress,
        transform: `translateY(${(1 - progress) * 18}px)`,
      }}
    >
      <PopText size={28} color={OUTLINE} weight={720}>
        {spec.subtitle}
      </PopText>
      <div style={{ height: 12 }} />
      <PopText size={54} color={OUTLINE} weight={900}>
        {spec.title}
      </PopText>
      <div
        style={{
          marginTop: 24,
          display: "inline-block",
          padding: "14px 22px 17px",
          background: accent,
          border: `6px solid ${OUTLINE}`,
          boxShadow: "8px 8px 0 rgba(32,39,43,0.18)",
          color: OUTLINE,
          fontFamily: PRODUCER_FONT_FAMILY,
          fontSize: spec.metric && spec.metric.length > 8 ? 52 : 70,
          lineHeight: 0.95,
          fontWeight: 950,
        }}
      >
        {spec.metric}
      </div>
    </div>
  );
};

const FooterNote: React.FC<{ note?: string; progress: number }> = ({ note, progress }) => {
  if (!note) return null;

  return (
    <div
      style={{
        position: "absolute",
        left: 148,
        right: 148,
        bottom: 106,
        padding: "16px 22px",
        background: "rgba(255,255,255,0.64)",
        border: `5px solid ${OUTLINE}`,
        color: OUTLINE,
        fontFamily: PRODUCER_FONT_FAMILY,
        fontSize: 30,
        lineHeight: 1.2,
        fontWeight: 760,
        opacity: progress,
        boxShadow: "8px 8px 0 rgba(32,39,43,0.16)",
      }}
    >
      {note}
    </div>
  );
};

export const PremiumProducerMotionGraphicOverlay: React.FC<{
  spec?: ProducerMotionGraphic;
  durationInFrames: number;
}> = ({ spec, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  if (!spec) return null;

  const fadeOutStart = Math.max(18, durationInFrames - Math.floor(fps * 0.55));
  const opacity = interpolate(
    frame,
    [0, 10, fadeOutStart, durationInFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE_OUT }
  );
  const progress = interpolate(
    frame,
    [0, Math.max(18, Math.floor(fps * 0.75))],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE_OUT }
  );
  const pop = spring({
    fps,
    frame,
    config: { damping: 15, stiffness: 135, mass: 0.72 },
  });
  const popProgress = Math.max(progress, Math.min(1, pop));
  const bg = backgrounds[spec.kind] || PINK;

  return (
    <AbsoluteFill style={{ opacity, pointerEvents: "none" }}>
      <Background color={bg} progress={progress} />
      <Illustration spec={spec} progress={popProgress} frame={frame} />
      <TitleBlock spec={spec} progress={popProgress} />
      <FooterNote note={(spec.notes ?? [])[0]} progress={progress} />
    </AbsoluteFill>
  );
};
