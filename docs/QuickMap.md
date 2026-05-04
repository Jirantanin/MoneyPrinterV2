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
  - Studio backend (FastAPI), API หลัก Podcast/Shorts, stream/progress
- `src/podcast_ui.html`
  - Studio Web UI หลัก
- `src/config.py`
  - config accessors/defaults, podcast settings, topic discovery wiring
- `src/classes/Podcast.py`
  - podcast pipeline หลัก
- `src/classes/YouTube.py`
  - upload/subtitle/render helpers บางส่วน
- `src/classes/Tts.py`
  - TTS provider routing

## Primary Flow (Podcast)

1. รับคำสั่งจาก UI (`src/podcast_ui.html`)
2. เริ่มงานผ่าน API ใน `src/podcast_server.py`
3. pipeline เรียก logic ใน `src/classes/Podcast.py`
4. ใช้ค่า config ผ่าน `src/config.py`
5. render/upload ผ่าน endpoint และ class ที่เกี่ยวข้อง

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

ใช้เมื่อปัญหาอยู่ที่ transition/motion/composition/output render โดยตรง

## Scope Labels (ใช้ลด token)

- `canonical`: ใช้ตอบ/ตัดสินใจ default
  - `docs/QuickMap.md`, `docs/Roadmap.md`, `docs/Configuration.md`, `AGENTS.md`
- `reference`: เปิดเมื่อจำเป็นต้องย้อนเหตุผลการออกแบบ
  - `docs/superpowers/plans/*`, `docs/superpowers/specs/*`
- `archived`: ไม่ใช้เป็นฐานงานใหม่
  - `docs/archive/*`, `src/legacy/*`

## Fast Triage (เวลาบั๊ก)

1. ยืนยันว่าเป็น Podcast หรือ Shorts ก่อน
2. ดู endpoint ที่ชนใน `src/podcast_server.py`
3. ไล่เข้า class หลัก (`Podcast.py` หรือ flow shorts)
4. เช็ก config key ใน `src/config.py`
5. ถ้าเป็นภาพ/transition/render ค่อยลง `remotion/*`
