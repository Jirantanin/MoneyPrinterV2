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

const VOYAGER_BG = "#05070b";
const VOYAGER_GOLD = "#d6b35a";
const VOYAGER_CREAM = "#e8e2d4";
const VOYAGER_BLUE = "#4d6680";

const phase = (frame: number, start: number, end: number) =>
  interpolate(frame, [start, end], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: EASE_OUT,
  });

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

const VoyagerLabel: React.FC<{
  children: React.ReactNode;
  x: number;
  y: number;
  opacity: number;
  align?: "left" | "right";
  width?: number;
}> = ({ children, x, y, opacity, align = "left", width }) => (
  <div
    style={{
      position: "absolute",
      left: align === "left" ? x : undefined,
      right: align === "right" ? x : undefined,
      top: y,
      color: VOYAGER_CREAM,
      fontFamily: PRODUCER_FONT_FAMILY,
      width,
      fontSize: 28,
      lineHeight: 1.16,
      fontWeight: 720,
      letterSpacing: 0.2,
      opacity,
      transform: `translateY(${(1 - opacity) * 12}px)`,
    }}
  >
    {children}
  </div>
);

const VoyagerRecordDecode: React.FC<{
  spec: ProducerMotionGraphic;
  frame: number;
  durationInFrames: number;
}> = ({ spec, frame, durationInFrames }) => {
  const intro = phase(frame, 0, 20);
  const playback = phase(frame, 12, 34);
  const hydrogen = phase(frame, 30, 52);
  const raster = phase(frame, 48, 70);
  const pulsars = phase(frame, 66, 92);
  const fadeOut = interpolate(
    frame,
    [Math.max(1, durationInFrames - 18), durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const diskRotation = interpolate(frame, [0, Math.max(1, durationInFrames)], [0, 16]);

  return (
    <AbsoluteFill
      style={{
        opacity: fadeOut,
        background: `radial-gradient(circle at 34% 48%, rgba(214,179,90,0.18), transparent 34%), ${VOYAGER_BG}`,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          left: 100,
          top: 72,
          color: VOYAGER_GOLD,
          fontFamily: PRODUCER_FONT_FAMILY,
          fontSize: 23,
          fontWeight: 720,
          letterSpacing: 2.4,
          opacity: intro,
        }}
      >
        VOYAGER GOLDEN RECORD
      </div>
      <div
        style={{
          position: "absolute",
          left: 100,
          top: 112,
          width: 930,
          color: VOYAGER_CREAM,
          fontFamily: PRODUCER_FONT_FAMILY,
          fontSize: 48,
          lineHeight: 1.12,
          fontWeight: 800,
          opacity: intro,
        }}
      >
        {spec.title || "คู่มือสำหรับผู้ไม่รู้จักเรา"}
      </div>

      <svg
        width="1920"
        height="1080"
        viewBox="0 0 1920 1080"
        style={{ position: "absolute", inset: 0 }}
      >
        <g
          opacity={intro}
          transform={`translate(510 590) rotate(${diskRotation})`}
        >
          <circle r="282" fill="#b99743" stroke="#f0d982" strokeWidth="8" />
          <circle r="230" fill="none" stroke="#7d652e" strokeWidth="2" />
          <circle r="174" fill="none" stroke="#8f7537" strokeWidth="2" />
          <circle r="118" fill="none" stroke="#765f2d" strokeWidth="2" />
          <circle r="62" fill="#0a0d12" stroke="#f0d982" strokeWidth="7" />
          {Array.from({ length: 56 }).map((_, index) => {
            const angle = (index / 56) * Math.PI * 2;
            const r1 = 82;
            const r2 = 266;
            return (
              <line
                key={index}
                x1={Math.cos(angle) * r1}
                y1={Math.sin(angle) * r1}
                x2={Math.cos(angle) * r2}
                y2={Math.sin(angle) * r2}
                stroke="#e2c56f"
                strokeWidth="1"
                opacity="0.22"
              />
            );
          })}
        </g>

        <g opacity={playback}>
          <line x1="730" y1="315" x2="586" y2="502" stroke={VOYAGER_CREAM} strokeWidth="8" />
          <circle cx="735" cy="306" r="18" fill={VOYAGER_GOLD} />
          <path d="M760 300 C890 270 952 286 1012 326" fill="none" stroke={VOYAGER_BLUE} strokeWidth="4" />
        </g>

        <g opacity={hydrogen} transform="translate(1170 330)">
          <circle cx="0" cy="0" r="43" fill="none" stroke={VOYAGER_CREAM} strokeWidth="5" />
          <circle cx="138" cy="0" r="43" fill="none" stroke={VOYAGER_CREAM} strokeWidth="5" />
          <line x1="48" y1="0" x2="90" y2="0" stroke={VOYAGER_GOLD} strokeWidth="6" />
          <polygon points="90,-10 112,0 90,10" fill={VOYAGER_GOLD} />
          <path d="M-18 -16 L18 16 M-18 16 L18 -16" stroke={VOYAGER_BLUE} strokeWidth="4" />
          <path d="M120 0 L156 0" stroke={VOYAGER_BLUE} strokeWidth="4" />
        </g>

        <g opacity={raster} transform="translate(1210 510)">
          <rect width="230" height="180" rx="7" fill="none" stroke={VOYAGER_CREAM} strokeWidth="5" />
          {Array.from({ length: 9 }).map((_, index) => (
            <line
              key={index}
              x1={18 + index * 24}
              y1="16"
              x2={18 + index * 24}
              y2="164"
              stroke={index < Math.floor(raster * 9) ? VOYAGER_GOLD : VOYAGER_BLUE}
              strokeWidth="5"
              opacity={index < Math.floor(raster * 9) ? 1 : 0.28}
            />
          ))}
          <circle cx="300" cy="90" r="64" fill="none" stroke={VOYAGER_GOLD} strokeWidth="6" />
        </g>

        <g opacity={pulsars} transform="translate(1488 818)">
          {Array.from({ length: 14 }).map((_, index) => {
            const angle = (index / 14) * Math.PI * 2 - Math.PI / 2;
            const length = 72 + (index % 5) * 20;
            return (
              <line
                key={index}
                x1="0"
                y1="0"
                x2={Math.cos(angle) * length}
                y2={Math.sin(angle) * length}
                stroke={index % 3 === 0 ? VOYAGER_GOLD : VOYAGER_CREAM}
                strokeWidth={index % 3 === 0 ? 5 : 3}
              />
            );
          })}
          <circle r="13" fill={VOYAGER_GOLD} />
        </g>
      </svg>

      <VoyagerLabel x={900} y={248} width={300} opacity={playback}>
        1&nbsp;&nbsp;วิธีเล่นแผ่นเสียง
      </VoyagerLabel>
      <VoyagerLabel x={170} y={286} width={520} opacity={hydrogen} align="right">
        2&nbsp;&nbsp;ไฮโดรเจนเป็นหน่วยเวลา
      </VoyagerLabel>
      <VoyagerLabel x={330} y={714} width={500} opacity={raster} align="right">
        3&nbsp;&nbsp;สร้างภาพจากเส้นสัญญาณ
      </VoyagerLabel>
      <VoyagerLabel x={170} y={914} width={500} opacity={pulsars} align="right">
        4&nbsp;&nbsp;พัลซาร์บอกตำแหน่งและยุค
      </VoyagerLabel>
    </AbsoluteFill>
  );
};

const VoyagerDeepTime: React.FC<{
  spec: ProducerMotionGraphic;
  frame: number;
  durationInFrames: number;
}> = ({ spec, frame, durationInFrames }) => {
  const intro = phase(frame, 0, 18);
  const mission = phase(frame, 14, 38);
  const deepTime = phase(frame, 34, 86);
  const fadeOut = interpolate(
    frame,
    [Math.max(1, durationInFrames - 18), durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const xStart = 210;
  const xMission = 620;
  const xEnd = 1710;
  const lineEnd = interpolate(deepTime, [0, 1], [xMission, xEnd]);

  return (
    <AbsoluteFill
      style={{
        opacity: fadeOut,
        background: `radial-gradient(circle at 80% 54%, rgba(77,102,128,0.2), transparent 35%), ${VOYAGER_BG}`,
        overflow: "hidden",
        color: VOYAGER_CREAM,
        fontFamily: PRODUCER_FONT_FAMILY,
      }}
    >
      <div style={{ position: "absolute", left: 110, top: 84, opacity: intro }}>
        <div style={{ color: VOYAGER_GOLD, fontSize: 23, fontWeight: 720, letterSpacing: 2.4 }}>
          VOYAGER / DEEP TIME
        </div>
        <div style={{ marginTop: 10, fontSize: 50, lineHeight: 1.1, fontWeight: 820 }}>
          {spec.title || "เวลาของยาน เทียบกับเวลาระหว่างดวงดาว"}
        </div>
      </div>

      <svg width="1920" height="1080" viewBox="0 0 1920 1080" style={{ position: "absolute", inset: 0 }}>
        <line x1={xStart} y1="570" x2={xEnd} y2="570" stroke="#1d2934" strokeWidth="16" />
        <line x1={xStart} y1="570" x2={xMission} y2="570" stroke={VOYAGER_GOLD} strokeWidth="10" opacity={mission} />
        <line x1={xMission} y1="570" x2={lineEnd} y2="570" stroke={VOYAGER_BLUE} strokeWidth="10" opacity={deepTime} />
        <circle cx={xStart} cy="570" r="18" fill={VOYAGER_CREAM} opacity={intro} />
        <circle cx={xMission} cy="570" r="22" fill={VOYAGER_GOLD} opacity={mission} />
        <circle cx={xEnd} cy="570" r="28" fill={VOYAGER_CREAM} opacity={deepTime} />
        {Array.from({ length: 14 }).map((_, index) => {
          const x = xMission + ((xEnd - xMission) * (index + 1)) / 15;
          return <circle key={index} cx={x} cy="570" r="3" fill={VOYAGER_CREAM} opacity={deepTime * 0.55} />;
        })}
        <path
          d="M 655 500 C 930 340, 1310 350, 1670 500"
          fill="none"
          stroke={VOYAGER_GOLD}
          strokeWidth="3"
          strokeDasharray="10 14"
          opacity={deepTime * 0.72}
        />
      </svg>

      <div style={{ position: "absolute", left: xStart - 42, top: 630, opacity: intro }}>
        <div style={{ color: VOYAGER_CREAM, fontSize: 30, fontWeight: 760 }}>1977</div>
        <div style={{ color: "#95a3ad", fontSize: 22, marginTop: 6 }}>ออกจากโลก</div>
      </div>
      <div style={{ position: "absolute", left: xMission - 82, top: 630, opacity: mission }}>
        <div style={{ color: VOYAGER_GOLD, fontSize: 36, fontWeight: 820 }}>เกือบ 49 ปี</div>
        <div style={{ color: "#aeb8bf", fontSize: 22, marginTop: 6 }}>อายุภารกิจในปี 2026</div>
      </div>
      <div
        style={{
          position: "absolute",
          right: 130,
          top: 402,
          width: 390,
          textAlign: "right",
          opacity: deepTime,
        }}
      >
        <div style={{ color: VOYAGER_CREAM, fontSize: 70, lineHeight: 0.98, fontWeight: 880 }}>
          ≈ 40,000 ปี
        </div>
        <div style={{ color: "#aeb8bf", fontSize: 24, lineHeight: 1.25, marginTop: 14 }}>
          ก่อนเข้าใกล้ระบบดาวอื่นครั้งหนึ่ง
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          left: 720,
          right: 110,
          bottom: 80,
          color: "#8e9aa4",
          fontSize: 22,
          textAlign: "right",
          opacity: deepTime,
        }}
      >
        ระยะบนเส้นถูกบีบอัดเพื่อให้มองเห็นความต่างของสเกลเวลา ไม่ใช่แผนที่ระยะทางจริง
      </div>
    </AbsoluteFill>
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

  if (spec.kind === "voyager_record_decode") {
    return <VoyagerRecordDecode spec={spec} frame={frame} durationInFrames={durationInFrames} />;
  }
  if (spec.kind === "voyager_deep_time") {
    return <VoyagerDeepTime spec={spec} frame={frame} durationInFrames={durationInFrames} />;
  }

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
