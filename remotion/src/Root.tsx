import React from "react";
import { Composition, registerRoot } from "remotion";
import { VideoShort } from "./VideoShort";
import { VideoPodcast } from "./VideoPodcast";
import { VideoProps, PodcastProps } from "./types";

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
    </>
  );
};

registerRoot(RemotionRoot);
