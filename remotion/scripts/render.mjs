import { readFileSync, mkdirSync, copyFileSync, existsSync, unlinkSync } from "node:fs";
import { writeFileSync } from "node:fs";
import { resolve, join, extname, dirname } from "node:path";
import { randomUUID } from "node:crypto";
import { execSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const remotionDir = resolve(__dirname, "..");
const projectRoot = resolve(remotionDir, "..");
const assetsDir = join(remotionDir, "public", "assets");

mkdirSync(assetsDir, { recursive: true });

const propsFilePath = process.argv[2];
if (!propsFilePath) {
  console.error("Usage: node scripts/render.mjs <props-file-path>");
  process.exit(1);
}

const rawProps = JSON.parse(readFileSync(propsFilePath, "utf8"));

// ─── Asset staging helpers ────────────────────────────────────────────────────
const stagedFiles = [];

function stageAsset(absolutePath) {
  if (!absolutePath) return null;
  const sourcePath = resolve(projectRoot, absolutePath);
  if (!existsSync(sourcePath)) return null;
  const ext = extname(sourcePath);
  const name = randomUUID() + ext;
  const dest = join(assetsDir, name);
  copyFileSync(sourcePath, dest);
  stagedFiles.push(dest);
  // Return path relative to remotion/public/ (staticFile() prefix)
  return "assets/" + name;
}

function cleanupStaged() {
  for (const f of stagedFiles) {
    try { unlinkSync(f); } catch (_) {}
  }
}

// ─── Composition selection ────────────────────────────────────────────────────
const composition = rawProps.composition || "VideoShort";
const isPodcast = composition === "VideoPodcast";
const fps = isPodcast ? 25 : 30;

// ─── Stage assets ─────────────────────────────────────────────────────────────
const imagePaths = (rawProps.imagePaths || [])
  .map((p) => stageAsset(p))
  .filter(Boolean);

const audioPath = stageAsset(rawProps.audioPath);
if (!audioPath) {
  console.error("ERROR: Audio file not found:", rawProps.audioPath);
  process.exit(1);
}

const bgmPath = rawProps.bgmPath ? stageAsset(rawProps.bgmPath) : undefined;

// Read SRT as string (avoids Chromium file:// restrictions entirely)
let srtContent = "";
if (rawProps.srtPath && existsSync(rawProps.srtPath)) {
  srtContent = readFileSync(rawProps.srtPath, "utf8");
} else if (rawProps.srtContent) {
  srtContent = rawProps.srtContent;
}

// Round up to integer frames (Remotion requires integer durationInFrames)
const durationInSeconds = Math.ceil(rawProps.durationInSeconds);

// ─── Build resolved props ─────────────────────────────────────────────────────
let resolvedProps;

if (isPodcast) {
  const scene0VideoPath = rawProps.scene0VideoPath ? stageAsset(rawProps.scene0VideoPath) : undefined;
  resolvedProps = {
    imagePaths,
    audioPath,
    sceneDurations: rawProps.sceneDurations || [],
    sceneTitles: rawProps.sceneTitles || [],
    durationInSeconds,
    ...(scene0VideoPath && { scene0VideoPath }),
    // V2 multi-asset props (omitted when absent so V1 renders unchanged)
    ...(rawProps.sceneImageCounts && { sceneImageCounts: rawProps.sceneImageCounts }),
    ...(rawProps.sceneAssetTypes && { sceneAssetTypes: rawProps.sceneAssetTypes }),
    ...(rawProps.sceneAssetDurations && { sceneAssetDurations: rawProps.sceneAssetDurations }),
  };
} else {
  resolvedProps = {
    topic: rawProps.topic,
    script: rawProps.script,
    category: rawProps.category || "default",
    imagePaths,
    audioPath,
    srtContent,
    bgmPath,
    durationInSeconds,
  };
}

const resolvedPropsPath = join(remotionDir, ".render-props-resolved.json");
writeFileSync(resolvedPropsPath, JSON.stringify(resolvedProps, null, 2), "utf8");

// Normalise Windows backslashes for shell safety
const outputPath = rawProps.outputPath.replace(/\\/g, "/");
const propsArg = resolvedPropsPath.replace(/\\/g, "/");

// ─── Invoke Remotion render ───────────────────────────────────────────────────
const cmd = [
  "npx", "remotion", "render",
  "src/Root.tsx",
  composition,
  `"${outputPath}"`,
  `--props="${propsArg}"`,
  `--fps=${fps}`,
  "--codec=h264",
  "--pixel-format=yuv420p",
  "--image-format=png",
  "--crf=18",
  "--concurrency=8",
  "--overwrite",
].join(" ");

console.log("[render.mjs] Running:", cmd);
try {
  execSync(cmd, {
    cwd: remotionDir,
    stdio: "inherit",
    shell: true,   // required on Windows: npx is a .cmd file
    timeout: 1_800_000,  // 30-minute safety valve (podcasts have many more frames)
  });
} finally {
  cleanupStaged();
  try { unlinkSync(resolvedPropsPath); } catch (_) {}
}

console.log("[render.mjs] Render complete:", outputPath);
