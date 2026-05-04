import React, { useMemo } from "react";
import { AbsoluteFill, Audio, OffthreadVideo, staticFile, useVideoConfig, useCurrentFrame, interpolate, spring } from "remotion";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { slide } from "@remotion/transitions/slide";
import { fade } from "@remotion/transitions/fade";
import { AssetType, PodcastProps } from "./types";
import { KenBurnsFrame, KB_CYCLE, SLIDE_DIRS, TRANSITION_FRAMES } from "./KenBurns";

// ─── Chapter Title Overlay ──────────────────────────────────────────────────
const ChapterTitle: React.FC<{ title: string; durationInFrames: number }> = ({ title, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  if (!title) return null;

  const cleanTitle = title.trim();
  if (!cleanTitle) return null;

  // Show for ~3.6s (or less if the scene is short)
  const showDuration = Math.max(24, Math.min(Math.floor(fps * 3.6), durationInFrames - 12));

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
        padding: "64px 72px",
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
            fontFamily: "Inter, Segoe UI, sans-serif",
            textShadow: "0 4px 16px rgba(0,0,0,0.35)",
          }}
        >
          {cleanTitle}
        </h2>
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
                  <OffthreadVideo
                    src={staticFile(scene0VideoPath)}
                    loop
                    volume={0}
                    style={{ width: "100%", height: "100%", objectFit: "cover" }}
                  />
                </AbsoluteFill>
              ) : (
                <KenBurnsFrame
                  imgPath={imgPath}
                  variant={KB_CYCLE[i % KB_CYCLE.length]}
                  durationInFrames={padded}
                />
              )}
              <ChapterTitle title={sceneTitles?.[i] || ""} durationInFrames={padded} />
            </TransitionSeries.Sequence>
            {i < n - 1 && (
              <TransitionSeries.Transition
                presentation={slide({ direction: SLIDE_DIRS[i % SLIDE_DIRS.length] })}
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
// Within a scene: fade transitions between assets.
// Between scenes: slide transitions (same as V1).
const PodcastSlideshowV2: React.FC<{
  imagePaths: string[];
  sceneDurations: number[];
  sceneTitles?: string[];
  scene0VideoPath?: string;
  sceneImageCounts: number[];
  sceneAssetTypes: AssetType[];
  sceneAssetDurations: number[];
}> = ({
  imagePaths,
  sceneDurations,
  sceneTitles,
  scene0VideoPath,
  sceneImageCounts,
  sceneAssetTypes,
  sceneAssetDurations,
}) => {
  const { fps } = useVideoConfig();

  if (imagePaths.length === 0) {
    return <AbsoluteFill style={{ backgroundColor: '#111' }} />;
  }

  const numScenes = sceneImageCounts.length;
  const minSceneFrames = Math.min(...sceneDurations.map(d => Math.ceil(d * fps)));
  const slideTf = numScenes > 1 ? Math.min(TRANSITION_FRAMES, Math.floor(minSceneFrames / 2)) : 0;
  const fadeTf = Math.min(15, Math.floor(minSceneFrames / 4));

  const sceneSlices = useMemo(() => {
    let offset = 0;
    return sceneImageCounts.map(count => {
      const slice = {
        paths: imagePaths.slice(offset, offset + count),
        types: sceneAssetTypes.slice(offset, offset + count),
        assetDurs: sceneAssetDurations.slice(offset, offset + count),
      };
      offset += count;
      return slice;
    });
  }, [imagePaths, sceneImageCounts, sceneAssetTypes, sceneAssetDurations]);

  const entries = useMemo(() => {
    const result: React.ReactNode[] = [];
    let globalAssetIdx = 0;

    for (let s = 0; s < numScenes; s++) {
      const { paths, types, assetDurs } = sceneSlices[s];
      const numAssets = paths.length;

      for (let a = 0; a < numAssets; a++) {
        const isLastAssetInScene = a === numAssets - 1;
        const isLastScene = s === numScenes - 1;
        const assetDur = assetDurs[a];
        const rawFrames = Math.ceil(assetDur * fps);

        let padded = rawFrames;
        if (!isLastAssetInScene && fadeTf > 0) padded += fadeTf;
        else if (isLastAssetInScene && !isLastScene && slideTf > 0) padded += slideTf;

        const imgPath = paths[a];
        const assetType = types[a];
        const isScene0Asset0 = s === 0 && a === 0;

        result.push(
          <TransitionSeries.Sequence key={`s${s}a${a}`} durationInFrames={padded}>
            {isScene0Asset0 && scene0VideoPath ? (
              <AbsoluteFill>
                <OffthreadVideo
                  src={staticFile(scene0VideoPath)}
                  loop
                  volume={0}
                  style={{ width: "100%", height: "100%", objectFit: "cover" }}
                />
              </AbsoluteFill>
            ) : assetType === "video" ? (
              <AbsoluteFill>
                <OffthreadVideo
                  src={staticFile(imgPath)}
                  loop
                  endAt={Math.floor(assetDur * fps)}
                  volume={0}
                  style={{ width: "100%", height: "100%", objectFit: "cover" }}
                />
              </AbsoluteFill>
            ) : (
              <KenBurnsFrame
                imgPath={imgPath}
                variant={KB_CYCLE[globalAssetIdx % KB_CYCLE.length]}
                durationInFrames={padded}
              />
            )}
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
                presentation={slide({ direction: SLIDE_DIRS[s % SLIDE_DIRS.length] })}
                timing={linearTiming({ durationInFrames: slideTf })}
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
  }, [sceneSlices, fps, slideTf, fadeTf, scene0VideoPath, sceneTitles, numScenes]);

  return <TransitionSeries>{entries}</TransitionSeries>;
};

// ─── Podcast Slideshow dispatcher ────────────────────────────────────────────
const PodcastSlideshow: React.FC<Pick<PodcastProps, 'imagePaths' | 'sceneDurations' | 'sceneTitles' | 'scene0VideoPath' | 'sceneImageCounts' | 'sceneAssetTypes' | 'sceneAssetDurations'>> = (props) => {
  if (props.sceneImageCounts && props.sceneImageCounts.length > 0 && props.sceneAssetTypes) {
    return (
      <PodcastSlideshowV2
        imagePaths={props.imagePaths}
        sceneDurations={props.sceneDurations}
        sceneTitles={props.sceneTitles}
        scene0VideoPath={props.scene0VideoPath}
        sceneImageCounts={props.sceneImageCounts}
        sceneAssetTypes={props.sceneAssetTypes}
        sceneAssetDurations={props.sceneAssetDurations ?? props.sceneDurations}
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
  return (
    <AbsoluteFill style={{ backgroundColor: "#000", width: 1920, height: 1080 }}>
      <PodcastSlideshow
        imagePaths={props.imagePaths}
        sceneDurations={props.sceneDurations}
        sceneTitles={props.sceneTitles}
        scene0VideoPath={props.scene0VideoPath}
        sceneImageCounts={props.sceneImageCounts}
        sceneAssetTypes={props.sceneAssetTypes}
        sceneAssetDurations={props.sceneAssetDurations}
      />
      {props.audioPath && <Audio src={staticFile(props.audioPath)} />}
    </AbsoluteFill>
  );
};
