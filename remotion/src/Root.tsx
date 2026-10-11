import React from "react";
import { Composition, registerRoot } from "remotion";
import { VideoPodcast } from "./VideoPodcast";
import { ClipShort } from "./ClipShort";
import { PodcastProps, ClipShortProps } from "./types";

const DEFAULT_PODCAST_PROPS: PodcastProps = {
  imagePaths: [],
  audioPath: "",
  sceneDurations: [30],
  durationInSeconds: 30,
  glossaryEntries: [],
};

const DEFAULT_CLIP_SHORT_PROPS: ClipShortProps = {
  videoPath: "",
  title: "คนรวยจะไม่ตาย?",
  subtitle: "SHORT DOCUMENTARY",
  srtContent: "1\n00:00:00,000 --> 00:00:03,000\nบริษัทหนึ่งกำลังใช้เงินหลายพันล้านดอลลาร์\n",
  keywordHighlights: [],
  startAtSeconds: 0,
  durationInSeconds: 45,
};

const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="VideoPodcast"
        component={VideoPodcast as any}
        durationInFrames={DEFAULT_PODCAST_PROPS.durationInSeconds * 25}
        fps={25}
        width={1920}
        height={1080}
        defaultProps={DEFAULT_PODCAST_PROPS}
        calculateMetadata={({ props }: any) => ({
          durationInFrames: Math.ceil((props as PodcastProps).durationInSeconds * 25),
        })}
      />
      <Composition
        id="ClipShort"
        component={ClipShort as any}
        durationInFrames={DEFAULT_CLIP_SHORT_PROPS.durationInSeconds * 30}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={DEFAULT_CLIP_SHORT_PROPS}
        calculateMetadata={({ props }: any) => ({
          durationInFrames: Math.ceil((props as ClipShortProps).durationInSeconds * 30),
        })}
      />
    </>
  );
};

registerRoot(RemotionRoot);
