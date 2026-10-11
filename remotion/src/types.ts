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
  | "queue"
  | "voyager_record_decode"
  | "voyager_deep_time";

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
  sceneAssetQualifications?: string[];
  sceneAssetCredits?: string[];
  sceneAssetFits?: Array<"cover" | "contain">;
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
