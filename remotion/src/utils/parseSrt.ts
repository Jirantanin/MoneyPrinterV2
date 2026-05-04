import { SrtEntry } from "../types";

function parseSrtTimestamp(ts: string): number {
  // Input: "00:00:03,280"  →  output: milliseconds
  const [hhmmss, ms] = ts.split(",");
  const [hh, mm, ss] = hhmmss.split(":").map(Number);
  return (hh * 3600 + mm * 60 + ss) * 1000 + Number(ms);
}

export function parseSrt(srtContent: string): SrtEntry[] {
  const entries: SrtEntry[] = [];
  // Normalise Windows CRLF → LF (Python writes SRT on Windows)
  const blocks = srtContent.replace(/\r\n/g, "\n").trim().split(/\n\n+/);

  for (const block of blocks) {
    const lines = block.split("\n");
    if (lines.length < 3) continue;

    const index = parseInt(lines[0], 10);
    const timeLine = lines[1].split(" --> ");
    if (timeLine.length < 2) continue;

    const text = lines.slice(2).join(" ").trim();
    if (!text) continue;

    entries.push({
      index,
      startMs: parseSrtTimestamp(timeLine[0].trim()),
      endMs: parseSrtTimestamp(timeLine[1].trim()),
      text,
    });
  }

  return entries.sort((a, b) => a.startMs - b.startMs);
}
