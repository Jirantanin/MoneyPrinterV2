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
  glossaryEntries?: GlossaryEntry[];
}
