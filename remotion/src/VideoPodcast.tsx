import React, { useMemo } from "react";
import { AbsoluteFill, Audio, Loop, OffthreadVideo, staticFile, useVideoConfig, useCurrentFrame, interpolate, spring } from "remotion";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { AssetType, GlossaryEntry, PodcastProps, ProducerMotionGraphic } from "./types";
import { KenBurnsFrame, TRANSITION_FRAMES } from "./KenBurns";
import { PremiumProducerMotionGraphicOverlay } from "./ProducerMotionGraphicOverlay";
import { PRODUCER_FONT_FAMILY, useProducerFonts } from "./producerFonts";

const PODCAST_MOTION_CYCLE = ['zoom-in', 'zoom-out'] as const;
const MOTION_GRAPHIC_COLORS = ["#f4c85f", "#64d7cb", "#ff8a72", "#9fb7ff"];

const AssetQualificationLabel: React.FC<{ text: string }> = ({ text }) => {
  if (!text.trim()) return null;

  return (
    <div
      style={{
        position: "absolute",
        left: 78,
        bottom: 66,
        zIndex: 20,
        maxWidth: 1420,
        padding: "12px 18px",
        borderLeft: "5px solid #f4c85f",
        borderRadius: 5,
        background: "rgba(7, 13, 22, 0.88)",
        boxShadow: "0 8px 26px rgba(0,0,0,0.42)",
        color: "#fff8e6",
        fontSize: 30,
        lineHeight: 1.22,
        fontWeight: 700,
        fontFamily: PRODUCER_FONT_FAMILY,
        pointerEvents: "none",
      }}
    >
      {text}
    </div>
  );
};

const AssetCreditLabel: React.FC<{ text: string }> = ({ text }) => {
  if (!text.trim()) return null;

  return (
    <div
      style={{
        position: "absolute",
        right: 78,
        bottom: 20,
        zIndex: 20,
        maxWidth: 1764,
        padding: "5px 9px",
        borderRadius: 3,
        background: "rgba(7, 13, 22, 0.76)",
        color: "rgba(255, 255, 255, 0.94)",
        fontSize: 17,
        lineHeight: 1.2,
        fontWeight: 500,
        fontFamily: PRODUCER_FONT_FAMILY,
        textAlign: "right",
        pointerEvents: "none",
      }}
    >
      {text}
    </div>
  );
};

const ProducerMotionGraphicOverlay: React.FC<{
  spec?: ProducerMotionGraphic;
  durationInFrames: number;
}> = ({ spec, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  if (!spec) return null;

  const fadeOutStart = Math.max(18, durationInFrames - Math.floor(fps * 0.5));
  const opacity = interpolate(
    frame,
    [0, 12, fadeOutStart, durationInFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const progress = interpolate(
    frame,
    [6, Math.max(28, Math.floor(durationInFrames * 0.45))],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const lift = interpolate(frame, [0, 18], [30, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const bars = spec.bars ?? [];
  const maxBar = Math.max(
    1,
    ...bars.map((bar) => Number(bar.max ?? bar.value ?? 0))
  );
  const notes = (spec.notes ?? []).slice(0, 3);

  const labelStyle: React.CSSProperties = {
    color: "#dfe9f4",
    fontSize: 28,
    lineHeight: 1.2,
    fontWeight: 650,
    fontFamily: PRODUCER_FONT_FAMILY,
  };

  return (
    <AbsoluteFill
      style={{
        opacity,
        background:
          "linear-gradient(90deg, rgba(0,0,0,0.58) 0%, rgba(0,0,0,0.2) 48%, rgba(0,0,0,0.66) 100%)",
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          position: "absolute",
          left: 74,
          top: 96,
          width: 620,
          transform: `translateY(${lift}px)`,
          padding: "30px 34px 32px",
          borderRadius: 18,
          background: "rgba(7, 13, 22, 0.76)",
          border: "1px solid rgba(240, 248, 255, 0.24)",
          boxShadow: "0 24px 60px rgba(0,0,0,0.45)",
        }}
      >
        {spec.title && (
          <div
            style={{
              color: "#fff8e6",
              fontSize: 44,
              lineHeight: 1.05,
              fontWeight: 850,
              fontFamily: PRODUCER_FONT_FAMILY,
              marginBottom: 12,
            }}
          >
            {spec.title}
          </div>
        )}
        {spec.subtitle && (
          <div style={{ ...labelStyle, color: "#9fd9ce", marginBottom: 20 }}>
            {spec.subtitle}
          </div>
        )}
        {spec.metric && (
          <div
            style={{
              color: "#f4c85f",
              fontSize: 78,
              lineHeight: 0.95,
              fontWeight: 900,
              fontFamily: PRODUCER_FONT_FAMILY,
              marginBottom: 20,
            }}
          >
            {spec.metric}
          </div>
        )}
        {bars.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
            {bars.map((bar, index) => {
              const width = Math.max(0, Math.min(1, Number(bar.value || 0) / maxBar)) * progress;
              const color = bar.color || MOTION_GRAPHIC_COLORS[index % MOTION_GRAPHIC_COLORS.length];
              return (
                <div key={`${bar.label}-${index}`}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      gap: 20,
                      marginBottom: 8,
                      ...labelStyle,
                    }}
                  >
                    <span>{bar.label}</span>
                    <span style={{ color }}>{bar.value}</span>
                  </div>
                  <div
                    style={{
                      height: 22,
                      borderRadius: 999,
                      background: "rgba(255,255,255,0.14)",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        width: `${width * 100}%`,
                        height: "100%",
                        borderRadius: 999,
                        background: color,
                        boxShadow: `0 0 28px ${color}`,
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
        {notes.length > 0 && (
          <div style={{ marginTop: 24, display: "flex", flexDirection: "column", gap: 10 }}>
            {notes.map((note, index) => (
              <div key={`${note}-${index}`} style={{ ...labelStyle, fontSize: 24, color: "#f3f7fb" }}>
                {note}
              </div>
            ))}
          </div>
        )}
      </div>

      {spec.kind === "orbit_slots" && (
        <div
          style={{
            position: "absolute",
            right: 120,
            top: 108,
            width: 780,
            height: 780,
            transform: `scale(${0.9 + progress * 0.1})`,
          }}
        >
          {[0, 1, 2, 3].map((ring) => {
            const size = 220 + ring * 145;
            const speed = ring % 2 === 0 ? 0.65 : -0.5;
            const rotation = frame * speed + ring * 38;
            return (
              <div
                key={ring}
                style={{
                  position: "absolute",
                  left: "50%",
                  top: "50%",
                  width: size,
                  height: size,
                  marginLeft: -size / 2,
                  marginTop: -size / 2,
                  borderRadius: "50%",
                  border: "2px solid rgba(180, 229, 255, 0.35)",
                  transform: `rotate(${rotation}deg)`,
                }}
              >
                <div
                  style={{
                    position: "absolute",
                    left: "50%",
                    top: -8,
                    width: 16,
                    height: 16,
                    borderRadius: "50%",
                    background: MOTION_GRAPHIC_COLORS[ring % MOTION_GRAPHIC_COLORS.length],
                    boxShadow: "0 0 24px rgba(255,255,255,0.8)",
                  }}
                />
              </div>
            );
          })}
          <div
            style={{
              position: "absolute",
              left: "50%",
              top: "50%",
              width: 156,
              height: 156,
              marginLeft: -78,
              marginTop: -78,
              borderRadius: "50%",
              background: "radial-gradient(circle, #66d6ff 0%, #244a71 60%, #101a2a 100%)",
              boxShadow: "0 0 80px rgba(102,214,255,0.45)",
            }}
          />
        </div>
      )}

      {spec.kind === "spectrum" && (
        <div
          style={{
            position: "absolute",
            right: 92,
            bottom: 100,
            width: 980,
            height: 280,
            display: "grid",
            gridTemplateColumns: "repeat(9, 1fr)",
            gap: 12,
          }}
        >
          {Array.from({ length: 9 }).map((_, index) => {
            const active = ((Math.floor(frame / 10) + index) % 9) / 8;
            const height = 70 + active * 180 * progress;
            return (
              <div
                key={index}
                style={{
                  alignSelf: "end",
                  height,
                  borderRadius: "12px 12px 0 0",
                  background: MOTION_GRAPHIC_COLORS[index % MOTION_GRAPHIC_COLORS.length],
                  opacity: 0.76,
                  boxShadow: "0 -10px 34px rgba(255,255,255,0.18)",
                }}
              />
            );
          })}
        </div>
      )}

      {spec.kind === "queue" && (
        <div
          style={{
            position: "absolute",
            right: 94,
            top: 134,
            width: 880,
            display: "grid",
            gridTemplateColumns: "repeat(6, 1fr)",
            gap: 18,
          }}
        >
          {Array.from({ length: 24 }).map((_, index) => {
            const filled = index / 24 < progress * 0.86;
            return (
              <div
                key={index}
                style={{
                  height: 76,
                  borderRadius: 14,
                  border: "1px solid rgba(255,255,255,0.2)",
                  background: filled
                    ? MOTION_GRAPHIC_COLORS[index % MOTION_GRAPHIC_COLORS.length]
                    : "rgba(255,255,255,0.08)",
                  boxShadow: filled ? "0 0 28px rgba(255,255,255,0.2)" : "none",
                }}
              />
            );
          })}
        </div>
      )}
    </AbsoluteFill>
  );
};

// ─── Chapter Title Overlay ──────────────────────────────────────────────────
const ChapterTitle: React.FC<{ title: string; durationInFrames: number }> = ({ title, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  if (!title) return null;

  const cleanTitle = title.trim();
  if (!cleanTitle) return null;

  // Keep chapter cards readable long enough for documentary section changes.
  const showDuration = Math.max(24, Math.min(Math.floor(fps * 6), durationInFrames - 12));

  // Fade in/out with a softer curve
  const opacity = interpolate(
    frame,
    [0, 14, Math.max(16, showDuration - 18), showDuration],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const rise = spring({
    frame,
    fps,
    config: { damping: 16, stiffness: 120, mass: 0.45 },
  });
  const scale = interpolate(rise, [0, 1], [0.96, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "flex-start",
        // Leave a clear gap above the lower-left asset qualification label.
        padding: "64px 72px 200px",
        opacity,
        transform: `translateY(${(1 - rise) * 42}px) scale(${scale})`,
      }}
    >
      <div
        style={{
          maxWidth: 1360,
          background:
            "linear-gradient(120deg, rgba(8,14,28,0.78) 0%, rgba(18,28,52,0.62) 55%, rgba(26,38,70,0.54) 100%)",
          border: "1px solid rgba(155, 201, 255, 0.3)",
          borderRadius: 22,
          padding: "22px 34px 24px 30px",
          boxShadow: "0 16px 38px rgba(0,0,0,0.45)",
          backdropFilter: "blur(6px)",
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
      >
        <div
          style={{
            width: 112,
            height: 4,
            borderRadius: 999,
            background: "linear-gradient(90deg, #8ed1ff 0%, #c8ecff 100%)",
          }}
        />
        <h2
          style={{
            margin: 0,
            color: "#f6fbff",
            fontSize: 66,
            lineHeight: 1.08,
            fontWeight: 800,
            letterSpacing: 0.3,
            fontFamily: PRODUCER_FONT_FAMILY,
            textShadow: "0 4px 16px rgba(0,0,0,0.35)",
          }}
        >
          {cleanTitle}
        </h2>
      </div>
    </AbsoluteFill>
  );
};

const GlossaryOverlay: React.FC<{ entries?: GlossaryEntry[] }> = ({ entries = [] }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentSecond = frame / fps;
  const entry = entries.find((item) => {
    const start = Number(item.start || 0);
    const duration = Number(item.duration || 5);
    return currentSecond >= start && currentSecond < start + duration;
  });

  if (!entry?.term || !entry?.meaning) return null;

  const localFrame = Math.max(0, frame - Math.floor(Number(entry.start || 0) * fps));
  const durationFrames = Math.max(24, Math.floor(Number(entry.duration || 5) * fps));
  const opacity = interpolate(
    localFrame,
    [0, 10, Math.max(12, durationFrames - 12), durationFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const lift = interpolate(localFrame, [0, 14], [24, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "flex-end",
        padding: "0 72px 68px 72px",
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          width: 620,
          maxWidth: 620,
          opacity,
          transform: `translateY(${lift}px)`,
          background: "rgba(5, 12, 24, 0.72)",
          border: "1px solid rgba(188, 225, 255, 0.32)",
          borderRadius: 12,
          padding: "18px 22px 20px",
          boxShadow: "0 14px 34px rgba(0,0,0,0.42)",
          backdropFilter: "blur(6px)",
          fontFamily: PRODUCER_FONT_FAMILY,
        }}
      >
        <div
          style={{
            color: "#9fd7ff",
            fontSize: 26,
            fontWeight: 800,
            lineHeight: 1.1,
            marginBottom: 8,
          }}
        >
          {entry.term}
        </div>
        <div
          style={{
            color: "#f3f8ff",
            fontSize: 31,
            fontWeight: 650,
            lineHeight: 1.22,
          }}
        >
          {entry.meaning}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ─── V1 Slideshow: one image per scene ──────────────────────────────────────
const PodcastSlideshowV1: React.FC<Pick<PodcastProps, 'imagePaths' | 'sceneDurations' | 'sceneTitles' | 'scene0VideoPath'>> = ({
  imagePaths,
  sceneDurations,
  sceneTitles,
  scene0VideoPath,
}) => {
  const { fps } = useVideoConfig();

  if (imagePaths.length === 0) {
    return <AbsoluteFill style={{ backgroundColor: '#111' }} />;
  }

  const n = imagePaths.length;
  const minSceneFrames = Math.min(...sceneDurations.map(d => Math.ceil(d * fps)));
  const tf = n > 1 ? Math.min(TRANSITION_FRAMES, Math.floor(minSceneFrames / 2)) : 0;

  return (
    <TransitionSeries>
      {imagePaths.map((imgPath, i) => {
        const rawFrames = Math.ceil(sceneDurations[i] * fps);
        const padded = n > 1 ? rawFrames + tf : rawFrames;

        return (
          <React.Fragment key={i}>
            <TransitionSeries.Sequence durationInFrames={padded}>
              {i === 0 && scene0VideoPath ? (
                <AbsoluteFill>
                  <Loop durationInFrames={Math.max(1, padded - 1)}>
                    <OffthreadVideo
                      src={staticFile(scene0VideoPath)}
                      volume={0}
                      style={{ width: "100%", height: "100%", objectFit: "cover" }}
                    />
                  </Loop>
                </AbsoluteFill>
              ) : (
                <KenBurnsFrame
                  imgPath={imgPath}
                  variant={PODCAST_MOTION_CYCLE[i % PODCAST_MOTION_CYCLE.length]}
                  durationInFrames={padded}
                  profile="documentary-readable"
                />
              )}
              <ChapterTitle title={sceneTitles?.[i] || ""} durationInFrames={padded} />
            </TransitionSeries.Sequence>
            {i < n - 1 && (
              <TransitionSeries.Transition
                presentation={fade()}
                timing={linearTiming({ durationInFrames: tf })}
              />
            )}
          </React.Fragment>
        );
      })}
    </TransitionSeries>
  );
};

// ─── V2 Slideshow: multiple assets per scene ─────────────────────────────────
// Use restrained motion and dissolves so documentary evidence remains readable.
const PodcastSlideshowV2: React.FC<{
  imagePaths: string[];
  sceneDurations: number[];
  sceneTitles?: string[];
  scene0VideoPath?: string;
  sceneImageCounts: number[];
  sceneAssetTypes: AssetType[];
  sceneAssetQualifications?: string[];
  sceneAssetCredits?: string[];
  sceneAssetFits?: Array<"cover" | "contain">;
  sceneAssetDurations: number[];
  producerMotionGraphics?: ProducerMotionGraphic[];
}> = ({
  imagePaths,
  sceneDurations,
  sceneTitles,
  scene0VideoPath,
  sceneImageCounts,
  sceneAssetTypes,
  sceneAssetQualifications = [],
  sceneAssetCredits = [],
  sceneAssetFits = [],
  sceneAssetDurations,
  producerMotionGraphics = [],
}) => {
  const { fps } = useVideoConfig();

  if (imagePaths.length === 0) {
    return <AbsoluteFill style={{ backgroundColor: '#111' }} />;
  }

  const numScenes = sceneImageCounts.length;
  const minSceneFrames = Math.min(...sceneDurations.map(d => Math.ceil(d * fps)));
  const sceneTf = numScenes > 1 ? Math.min(TRANSITION_FRAMES, Math.floor(minSceneFrames / 2)) : 0;
  const fadeTf = Math.min(15, Math.floor(minSceneFrames / 4));

  const sceneSlices = useMemo(() => {
    let offset = 0;
    const slices = sceneImageCounts.map(count => {
      const paths = imagePaths.slice(offset, offset + count);
      const types = sceneAssetTypes.slice(offset, offset + count);
      const qualifications = sceneAssetQualifications.slice(offset, offset + count);
      const credits = sceneAssetCredits.slice(offset, offset + count);
      const fits = sceneAssetFits.slice(offset, offset + count);
      const assetDurs = sceneAssetDurations.slice(offset, offset + count);
      offset += count;

      const compacted: Array<{ path: string; type: AssetType; qualification: string; credit: string; fit: "cover" | "contain"; duration: number; assetIndex: number }> = [];
      paths.forEach((path, index) => {
        const type = types[index];
        const qualification = qualifications[index] ?? "";
        const credit = credits[index] ?? "";
        const fit = fits[index] === "contain" ? "contain" : "cover";
        const duration = assetDurs[index] ?? 0;
        const previous = compacted[compacted.length - 1];
        if (previous && previous.path === path && previous.type === type && previous.qualification === qualification && previous.credit === credit && previous.fit === fit && type === "image") {
          previous.duration += duration;
          return;
        }
        compacted.push({ path, type, qualification, credit, fit, duration, assetIndex: index });
      });

      return {
        paths: compacted.map((asset) => asset.path),
        types: compacted.map((asset) => asset.type),
        qualifications: compacted.map((asset) => asset.qualification),
        credits: compacted.map((asset) => asset.credit),
        fits: compacted.map((asset) => asset.fit),
        assetDurs: compacted.map((asset) => asset.duration),
        assetIndexes: compacted.map((asset) => asset.assetIndex),
      };
    });

    for (let sceneIndex = 1; sceneIndex < slices.length; sceneIndex++) {
      const current = slices[sceneIndex];
      if ((sceneTitles?.[sceneIndex] || "").trim() || current.paths.length === 0) {
        continue;
      }

      let previousIndex = sceneIndex - 1;
      while (previousIndex >= 0 && slices[previousIndex].paths.length === 0) {
        previousIndex--;
      }
      if (previousIndex < 0) {
        continue;
      }

      const previous = slices[previousIndex];
      const previousAssetIndex = previous.paths.length - 1;
      const sameStillContinues =
        previousAssetIndex >= 0 &&
        previous.paths[previousAssetIndex] === current.paths[0] &&
        previous.types[previousAssetIndex] === "image" &&
        current.types[0] === "image" &&
        previous.qualifications[previousAssetIndex] === current.qualifications[0] &&
        previous.credits[previousAssetIndex] === current.credits[0] &&
        previous.fits[previousAssetIndex] === current.fits[0];

      if (sameStillContinues) {
        previous.assetDurs[previousAssetIndex] += current.assetDurs[0];
        current.paths.shift();
        current.types.shift();
        current.qualifications.shift();
        current.credits.shift();
        current.fits.shift();
        current.assetDurs.shift();
        current.assetIndexes.shift();
      }
    }

    return slices;
  }, [imagePaths, sceneImageCounts, sceneAssetTypes, sceneAssetQualifications, sceneAssetCredits, sceneAssetFits, sceneAssetDurations, sceneTitles]);

  const entries = useMemo(() => {
    const result: React.ReactNode[] = [];
    let globalAssetIdx = 0;

    for (let s = 0; s < numScenes; s++) {
      const { paths, types, qualifications, credits, fits, assetDurs, assetIndexes } = sceneSlices[s];
      const numAssets = paths.length;

      for (let a = 0; a < numAssets; a++) {
        const isLastAssetInScene = a === numAssets - 1;
        const isLastScene = s === numScenes - 1;
        const assetDur = assetDurs[a];
        const rawFrames = Math.ceil(assetDur * fps);

        let padded = rawFrames;
        if (!isLastAssetInScene && fadeTf > 0) padded += fadeTf;
        else if (isLastAssetInScene && !isLastScene && sceneTf > 0) padded += sceneTf;

        const imgPath = paths[a];
        const assetType = types[a];
        const isScene0Asset0 = s === 0 && a === 0;
        const assetIndex = assetIndexes[a] ?? a;
        const motionGraphic = producerMotionGraphics.find((spec) => {
          const sameScene = Number(spec.sceneIndex) === s;
          const sameAsset =
            spec.assetIndex === undefined || Number(spec.assetIndex) === assetIndex;
          return sameScene && sameAsset;
        });

        result.push(
          <TransitionSeries.Sequence key={`s${s}a${a}`} durationInFrames={padded}>
            <AbsoluteFill>
              {isScene0Asset0 && scene0VideoPath ? (
                <OffthreadVideo
                  src={staticFile(scene0VideoPath)}
                  endAt={Math.max(1, padded)}
                  volume={0}
                  style={{ width: "100%", height: "100%", objectFit: "cover" }}
                />
              ) : assetType === "video" ? (
                <OffthreadVideo
                  src={staticFile(imgPath)}
                  endAt={Math.max(1, padded)}
                  volume={0}
                  style={{ width: "100%", height: "100%", objectFit: "cover" }}
                />
              ) : (
                <KenBurnsFrame
                  imgPath={imgPath}
                  variant={PODCAST_MOTION_CYCLE[globalAssetIdx % PODCAST_MOTION_CYCLE.length]}
                  durationInFrames={padded}
                  profile="documentary-readable"
                  fit={fits[a] ?? "cover"}
                />
              )}
              <AssetQualificationLabel text={qualifications[a] ?? ""} />
              <AssetCreditLabel text={credits[a] ?? ""} />
              <PremiumProducerMotionGraphicOverlay spec={motionGraphic} durationInFrames={padded} />
            </AbsoluteFill>
            {a === 0 && (
              <ChapterTitle title={sceneTitles?.[s] || ""} durationInFrames={padded} />
            )}
          </TransitionSeries.Sequence>
        );

        const isVeryLast = isLastAssetInScene && isLastScene;
        if (!isVeryLast) {
          if (isLastAssetInScene) {
            result.push(
              <TransitionSeries.Transition
                key={`tr_s${s}a${a}`}
                presentation={fade()}
                timing={linearTiming({ durationInFrames: sceneTf })}
              />
            );
          } else {
            result.push(
              <TransitionSeries.Transition
                key={`tr_s${s}a${a}`}
                presentation={fade()}
                timing={linearTiming({ durationInFrames: fadeTf })}
              />
            );
          }
        }

        globalAssetIdx++;
      }
    }

    return result;
  }, [sceneSlices, fps, sceneTf, fadeTf, scene0VideoPath, sceneTitles, numScenes, producerMotionGraphics]);

  return <TransitionSeries>{entries}</TransitionSeries>;
};

// ─── Podcast Slideshow dispatcher ────────────────────────────────────────────
const PodcastSlideshow: React.FC<Pick<PodcastProps, 'imagePaths' | 'sceneDurations' | 'sceneTitles' | 'scene0VideoPath' | 'sceneImageCounts' | 'sceneAssetTypes' | 'sceneAssetQualifications' | 'sceneAssetCredits' | 'sceneAssetFits' | 'sceneAssetDurations' | 'producerMotionGraphics'>> = (props) => {
  if (props.sceneImageCounts && props.sceneImageCounts.length > 0 && props.sceneAssetTypes) {
    return (
      <PodcastSlideshowV2
        imagePaths={props.imagePaths}
        sceneDurations={props.sceneDurations}
        sceneTitles={props.sceneTitles}
        scene0VideoPath={props.scene0VideoPath}
        sceneImageCounts={props.sceneImageCounts}
        sceneAssetTypes={props.sceneAssetTypes}
        sceneAssetQualifications={props.sceneAssetQualifications}
        sceneAssetCredits={props.sceneAssetCredits}
        sceneAssetFits={props.sceneAssetFits}
        sceneAssetDurations={props.sceneAssetDurations ?? props.sceneDurations}
        producerMotionGraphics={props.producerMotionGraphics}
      />
    );
  }
  return (
    <PodcastSlideshowV1
      imagePaths={props.imagePaths}
      sceneDurations={props.sceneDurations}
      sceneTitles={props.sceneTitles}
      scene0VideoPath={props.scene0VideoPath}
    />
  );
};

// ─── Root composition ────────────────────────────────────────────────────────
export const VideoPodcast: React.FC<PodcastProps> = (props) => {
  useProducerFonts();

  return (
    <AbsoluteFill style={{ backgroundColor: "#000", width: 1920, height: 1080 }}>
      <PodcastSlideshow
        imagePaths={props.imagePaths}
        sceneDurations={props.sceneDurations}
        sceneTitles={props.sceneTitles}
        scene0VideoPath={props.scene0VideoPath}
        sceneImageCounts={props.sceneImageCounts}
        sceneAssetTypes={props.sceneAssetTypes}
        sceneAssetQualifications={props.sceneAssetQualifications}
        sceneAssetCredits={props.sceneAssetCredits}
        sceneAssetFits={props.sceneAssetFits}
        sceneAssetDurations={props.sceneAssetDurations}
        producerMotionGraphics={props.producerMotionGraphics}
      />
      <GlossaryOverlay entries={props.glossaryEntries} />
      {props.audioPath && <Audio src={staticFile(props.audioPath)} />}
    </AbsoluteFill>
  );
};
