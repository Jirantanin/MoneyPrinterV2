import { useEffect, useState } from "react";
import { continueRender, delayRender, staticFile } from "remotion";

export const PRODUCER_FONT_FAMILY =
  '"Noto Sans Thai", "Leelawadee UI", Tahoma, Arial, sans-serif';

const FONT_FAMILY_NAME = "Noto Sans Thai";
const FONT_FILES = [
  { file: "NotoSansThai-Regular.ttf", weight: "400" },
  { file: "NotoSansThai-Medium.ttf", weight: "500" },
  { file: "NotoSansThai-SemiBold.ttf", weight: "600" },
  { file: "NotoSansThai-Bold.ttf", weight: "700" },
  { file: "NotoSansThai-ExtraBold.ttf", weight: "800" },
] as const;

let producerFontsReady = false;
let producerFontPromise: Promise<void> | null = null;

const loadProducerFonts = () => {
  if (producerFontsReady) return Promise.resolve();
  if (producerFontPromise) return producerFontPromise;

  producerFontPromise = (async () => {
    if (typeof document === "undefined" || typeof FontFace === "undefined") {
      producerFontsReady = true;
      return;
    }

    const faces = await Promise.all(
      FONT_FILES.map(async ({ file, weight }) => {
        const face = new FontFace(
          FONT_FAMILY_NAME,
          `url("${staticFile(`fonts/noto-sans-thai/${file}`)}") format("truetype")`,
          {
            display: "block",
            style: "normal",
            weight,
          }
        );
        return face.load();
      })
    );

    const fontSet = document.fonts as FontFaceSet & {
      add: (font: FontFace) => void;
    };

    for (const face of faces) {
      fontSet.add(face);
    }

    await fontSet.ready;
    producerFontsReady = true;
  })();

  return producerFontPromise;
};

export const useProducerFonts = () => {
  const [fontHandle] = useState(() =>
    producerFontsReady ? null : delayRender("Loading producer Thai fonts")
  );

  useEffect(() => {
    if (fontHandle === null) return;

    loadProducerFonts()
      .catch((error) => {
        console.error("Failed to load producer fonts", error);
      })
      .finally(() => {
        continueRender(fontHandle);
      });
  }, [fontHandle]);
};
