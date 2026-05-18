import React from "react";
import { Composition, registerRoot } from "remotion";
import { VideoShort } from "./VideoShort";
import { VideoPodcast } from "./VideoPodcast";
import { ClipShort } from "./ClipShort";
import { StillImageShort } from "./StillImageShort";
import { VideoProps, PodcastProps, ClipShortProps, StillImageShortProps } from "./types";

const DEFAULT_PROPS: VideoProps = {
  topic: "Test Topic",
  script: "This is a test script for preview purposes.",
  category: "default",
  imagePaths: [],
  audioPath: "",
  srtContent: "1\n00:00:00,000 --> 00:00:03,000\nTest subtitle.\n",
  bgmPath: undefined,
  durationInSeconds: 30,
};

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

const DEFAULT_STILL_IMAGE_SHORT_PROPS: StillImageShortProps = {
  imagePaths: [],
  sceneDurations: [40],
  overlayEvents: [],
  durationInSeconds: 40,
};

const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="VideoShort"
        component={VideoShort as any}
        durationInFrames={DEFAULT_PROPS.durationInSeconds * 30}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={DEFAULT_PROPS}
        calculateMetadata={({ props }: any) => ({
          durationInFrames: Math.ceil((props as VideoProps).durationInSeconds * 30),
        })}
      />
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
      <Composition
        id="StillImageShort"
        component={StillImageShort as any}
        durationInFrames={DEFAULT_STILL_IMAGE_SHORT_PROPS.durationInSeconds * 30}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={DEFAULT_STILL_IMAGE_SHORT_PROPS}
        calculateMetadata={({ props }: any) => ({
          durationInFrames: Math.ceil((props as StillImageShortProps).durationInSeconds * 30),
        })}
      />
    </>
  );
};

registerRoot(RemotionRoot);
