import { VideoCategory } from "./types";

export interface CategoryPreset {
  badgeLabel: string;
  badgeColor: string;
  subtitleAnimation: 'fade' | 'slide_up' | 'pop';
  overlayStyle: 'clean' | 'breaking_news_ticker' | 'glitch';
  accentColor: string;
}

const PRESETS: Record<VideoCategory, CategoryPreset> = {
  breaking_news: {
    badgeLabel: "🔴 BREAKING NEWS",
    badgeColor: "#cc0000",
    subtitleAnimation: "slide_up",
    overlayStyle: "breaking_news_ticker",
    accentColor: "#ff4444",
  },
  science_facts: {
    badgeLabel: "🔬 SCIENCE FACTS",
    badgeColor: "#1a5276",
    subtitleAnimation: "fade",
    overlayStyle: "clean",
    accentColor: "#3498db",
  },
  weird_viral: {
    badgeLabel: "🔥 WEIRD & VIRAL",
    badgeColor: "#e67e22",
    subtitleAnimation: "pop",
    overlayStyle: "glitch",
    accentColor: "#ff9500",
  },
  default: {
    badgeLabel: "",
    badgeColor: "#222222",
    subtitleAnimation: "fade",
    overlayStyle: "clean",
    accentColor: "#ffffff",
  },
};

export function getPreset(category: VideoCategory): CategoryPreset {
  return PRESETS[category];
}
