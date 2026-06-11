export type VideoCategory = 'breaking_news' | 'science_facts' | 'weird_viral' | 'default';

export interface VideoProps {
  topic: string;
  script: string;
  category: VideoCategory;
  imagePaths: string[];        // paths relative to remotion/public/ (e.g. "assets/abc.png")
  audioPath: string;           // relative path within remotion/public/ (e.g. "assets/abc.wav")
  srtContent: string;          // full SRT file content as a string
  bgmPath?: string;            // relative path within remotion/public/ (optional)
  durationInSeconds: number;
}

export interface SrtEntry {
  index: number;
  startMs: number;
  endMs: number;
  text: string;
}

export type AssetType = "image" | "video";

export type ProducerMotionGraphicKind =
  | "bar_share"
  | "orbit_slots"
  | "spectrum"
  | "queue";

export interface ProducerMotionGraphicBar {
  label: string;
  value: number;
  max?: number;
  color?: string;
}

export interface ProducerMotionGraphic {
  sceneIndex: number;
  assetIndex?: number;
  kind: ProducerMotionGraphicKind;
  title?: string;
  subtitle?: string;
  metric?: string;
  bars?: ProducerMotionGraphicBar[];
  notes?: string[];
}

export interface GlossaryEntry {
  term: string;
  meaning: string;
  start: number;
  duration?: number;
}

export interface PodcastProps {
  imagePaths: string[];
  audioPath: string;
  sceneDurations: number[];
  sceneTitles?: string[];
  durationInSeconds: number;
  scene0VideoPath?: string;
  sceneImageCounts?: number[];
  sceneAssetTypes?: AssetType[];
  sceneAssetDurations?: number[];
  producerMotionGraphics?: ProducerMotionGraphic[];
  glossaryEntries?: GlossaryEntry[];
}

export interface ClipShortProps {
  videoPath: string;
  title: string;
  subtitle?: string;
  srtContent: string;
  keywordHighlights?: string[];
  startAtSeconds: number;
  durationInSeconds: number;
}

export interface StillImageShortOverlay {
  text: string;
  startSeconds: number;
  durationSeconds: number;
  kind?: "headline" | "metric" | "label" | "question";
  y?: number;
  fontSize?: number;
  color?: string;
}

export interface StillImageShortFooterCover {
  enabled?: boolean;
  title?: string;
  subtitle?: string;
  metric?: string;
  height?: number;
}

export interface StillImageShortProps {
  imagePaths: string[];
  assetTypes?: AssetType[];
  sceneDurations: number[];
  overlayEvents?: StillImageShortOverlay[];
  footerCover?: StillImageShortFooterCover;
  audioPath?: string;
  durationInSeconds: number;
}
