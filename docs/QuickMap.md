# MoneyPrinterV2 QuickMap

เอกสารสั้นสำหรับเริ่มงานเร็วและลดการเปิดไฟล์เกินจำเป็น

## Canonical Docs (อ่านก่อน)

1. `docs/QuickMap.md` (ไฟล์นี้)
2. `docs/Roadmap.md`
3. `docs/Configuration.md`
4. `docs/API-Surface.md`
5. `AGENTS.md`

## Runtime Truth (โค้ดหลัก)

- `src/podcast_server.py`
  - Studio backend (FastAPI), API หลัก Podcast/Shorts, stream/progress, restore state
- `src/podcast_ui.html`
  - Studio Web UI หลัก
- `src/ui/podcast-v2-*.js` และ `src/ui/podcast_v2_component.html`
  - logic/UI เฉพาะ PodcastV2 เช่น settings, tone preset, cost panel, render preview
- `src/config.py`
  - config accessors/defaults, PodcastV2 system settings, provider keys, topic discovery wiring
- `src/classes/PodcastV2.py`
  - long-form PodcastV2 pipeline ปัจจุบัน: script/QC/assets/metadata/thumbnail/render/upload
- `src/classes/Podcast.py`
  - Podcast V1 pipeline
- `src/classes/YouTube.py`
  - upload/subtitle/render helpers บางส่วน
- `src/classes/Tts.py`
  - TTS provider routing
- `src/visual_planner.py`
  - deterministic visual plan, stock keywords, AI fallback prompts, `visual_plan.json`
- `src/pexels_provider.py`, `src/pixabay_provider.py`, `src/runware_provider.py`
  - stock video และ FLUX.1 fallback image providers
- `src/runtime_trace.py`
  - API usage trace และ cost estimation summary

## Primary Flow (PodcastV2)

1. รับคำสั่งจาก UI (`src/podcast_ui.html`)
2. เริ่มงานผ่าน `POST /api/v2/generate` ใน `src/podcast_server.py`
3. สร้าง `PodcastV2` แล้วรัน step หลัก: script -> assets -> metadata -> thumbnail -> render
4. manual script mode ใช้ section parser/QC แล้วเขียน `script_sections.json` และ `visual_beats.json`
5. asset generation เขียน `visual_plan.json`, ลอง `Pexels -> Pixabay -> Runware FLUX.1`
6. render ผ่าน Remotion ไปที่ `final_unnormalized.mp4` ก่อน normalize เป็น `final.mp4`
7. terminal cost summary ถูก emit ผ่าน SSE และ persist เป็น `cost_summary.json`

## Primary Flow (Podcast V1)

ใช้เมื่อเจอ endpoint `/api/*` ที่ไม่ใช่ `/api/v2/*`.

1. รับคำสั่งจาก UI
2. เริ่มงานผ่าน API ใน `src/podcast_server.py`
3. pipeline เรียก logic ใน `src/classes/Podcast.py`
4. render/upload ผ่าน endpoint และ class ที่เกี่ยวข้อง

## API Surface ที่ใช้บ่อย

- `POST /api/generate`
- `GET /api/stream/{episode_id}`
- `GET /api/episode/{episode_id}`
- `POST /api/redo/{episode_id}`
- `POST /api/asset/{episode_id}/regen`
- `POST /api/upload/{episode_id}`
- `POST /api/mark-uploaded/{episode_id}`
- `POST /api/v2/generate`
- `GET /api/v2/stream/{episode_id}`
- `GET /api/v2/episode/{episode_id}`
- `POST /api/v2/upload/{episode_id}`

## Shorts Surface ที่ใช้บ่อย

- `POST /shorts/api/generate`
- `GET /shorts/api/stream/{short_id}`
- `GET /shorts/api/episode/{short_id}`
- `POST /shorts/api/upload/{short_id}`

## Remotion Area

- `remotion/src/VideoPodcast.tsx`
- `remotion/src/Root.tsx`
- `remotion/scripts/render.mjs`

ใช้เมื่อปัญหาอยู่ที่ transition/motion/composition/output render โดยตรง.
PodcastV2 ควรใช้ Node 22 path สำหรับ Remotion validation.

## PodcastV2 Episode Artifacts

โฟลเดอร์ปกติอยู่ที่ `.mp/podcast_v2_YYYYMMDD_HHMMSS`.

- `script.json`: source of truth ของ scenes/visual beats สำหรับ render
- `script_qc.json`, `script_format_qc.json`, `script_length_qc.json`: report/checkpoint ของ script lane
- `manual_script_clean.txt`: manual script หลัง clean แล้ว
- `script_sections.json`: section metadata จาก manual script mode
- `visual_beats.json`: beat list ที่แปลงจาก sections
- `visual_plan.json`: stock keywords และ AI fallback prompts ต่อ asset
- `stock_query_report.json`: log การลอง Pexels/Pixabay ต่อ keyword
- `scene_NN.wav`: narration ต่อ scene
- `scene_NN_K.png` / `scene_NN_K.mp4`: per-scene visual assets
- `merged_audio.wav`, `merged_audio_with_bed.wav`: audio รวมก่อน render
- `final_unnormalized.mp4`: Remotion raw render ก่อน normalize
- `final.mp4`: expected upload-ready render หลัง normalize
- `metadata.json`, `state.json`, `cost_summary.json`: metadata/state/cost trace

## Scope Labels (ใช้ลด token)

- `canonical`: ใช้ตอบ/ตัดสินใจ default
  - `docs/QuickMap.md`, `docs/Roadmap.md`, `docs/Configuration.md`, `AGENTS.md`
- `reference`: เปิดเมื่อจำเป็นต้องย้อนเหตุผลการออกแบบ
  - `docs/superpowers/plans/*`, `docs/superpowers/specs/*`
- `archived`: ไม่ใช้เป็นฐานงานใหม่
  - `docs/archive/*`, `src/legacy/*`

## Fast Triage (เวลาบั๊ก)

1. ยืนยันว่าเป็น PodcastV2, Podcast V1, หรือ Shorts ก่อน
2. ถ้าเป็น PodcastV2 ให้เริ่มที่ `src/podcast_server.py` route `/api/v2/*`
3. ไล่เข้า `src/classes/PodcastV2.py` ตาม step ที่ล้ม
4. ถ้าเป็น script/manual-script ให้ดู `script_*qc.json`, `script_sections.json`, `visual_beats.json`
5. ถ้าเป็น asset/B-roll ให้ดู `visual_plan.json`, `stock_query_report.json`, provider files
6. ถ้าเป็น render ให้ดู `remotion/*`, `final_unnormalized.mp4`, `final.mp4`, และ Node runtime
7. ถ้าเป็น cost ให้ดู `src/runtime_trace.py`, SSE `cost_summary`, และ `cost_summary.json`
