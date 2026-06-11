# MoneyPrinterV2 API Surface

สรุป API ที่ใช้บ่อยใน Studio เพื่อเริ่มงานและ debug ได้เร็ว

## Base

- Studio ปกติรันที่ `http://127.0.0.1:8899`
- Backend หลักอยู่ที่ `src/podcast_server.py`

## Podcast V1

### Generate + Stream

- `POST /api/generate`
  - body ที่ใช้บ่อย:
    - `topic` (required เมื่อ `script_mode=false`)
    - `script_mode` (bool)
    - `raw_script` (required เมื่อ `script_mode=true`)
    - `title` (optional; ใช้กับ script mode)
    - `mode` (`auto` | `step`)
    - `language` (`Thai` | `English`)
    - `tts_source` (optional)
    - `creative_direction` (optional)
    - `visual_style` (optional)
  - response:
    - `{ "episode_id": "podcast_YYYYMMDD_HHMMSS" }`

- `GET /api/stream/{episode_id}`
  - SSE สำหรับ progress/log ระหว่าง pipeline

- `GET /api/episode/{episode_id}`
  - state ทั้งก้อนของ episode (status/steps/metadata/error/paths)

### Control + Recovery

- `POST /api/resume/{episode_id}` เริ่มต่อจาก step ที่ยังไม่เสร็จ
- `POST /api/redo/{episode_id}` รันซ้ำตาม logic ของระบบ
- `POST /api/asset/{episode_id}/regen` regenerate asset เฉพาะจุด
- `POST /api/approve/{episode_id}` ใช้ใน step mode
- `POST /api/cancel/{episode_id}` ยกเลิก pipeline

### Publish

- `POST /api/upload/{episode_id}`
  - body ที่ใช้บ่อย:
    - `privacy_status` (default `public`)
    - `publish_at` (optional; schedule)
- `POST /api/mark-uploaded/{episode_id}`
  - ใช้ mark ว่าอัปโหลดภายนอกแล้ว

## Podcast V2

- `POST /api/v2/generate`
  - body ที่ใช้บ่อย:
    - `topic` (required เมื่อ `script_mode=false`)
    - `script_mode` (bool)
    - `raw_script` (required เมื่อ `script_mode=true`)
    - `title` (optional; ใช้กับ script mode)
    - `mode` (`auto` | `step`)
    - `creative_direction` (optional)
    - `visual_style` (optional)
    - `tts_tone_preset` (optional; default `natural_storyteller`)
    - `system_settings` (optional; partial settings ที่จะ merge เข้า podcast settings)
  - response:
    - `{ "episode_id": "podcast_v2_YYYYMMDD_HHMMSS" }`
- `GET /api/v2/stream/{episode_id}` SSE
  - events ที่ใช้จริง:
    - `log`
    - `step_start`
    - `step_done`
    - `step_error`
    - `resume`
    - `waiting_approval`
    - `cancelled`
    - `cost_summary`
    - `complete`
    - `error`
- `GET /api/v2/episode/{episode_id}`
  - state episode; delegates ไป shared episode handler
  - field ที่ frontend ใช้บ่อย:
    - `status`
    - `step_states`
    - `metadata`
    - `script_qc`
    - `beat_qc`
    - `tts_tone_preset`
    - `estimated_cost`
    - `video_url` เมื่อมี `final.mp4`
- `POST /api/v2/upload/{episode_id}`
  - body: `privacy_status`, `publish_at`
  - ต้องมี `final.mp4` ใน episode dir ก่อน upload

### PodcastV2 Episode Files

ไฟล์ที่มักต้องเปิดเวลา debug อยู่ใน `.mp/podcast_v2_YYYYMMDD_HHMMSS`.

- `script.json`: scenes ที่ pipeline/render ใช้
- `script_qc.json`: script quality report
- `script_format_qc.json` / `script_length_qc.json`: manual-script validation
- `script_sections.json`: sections จาก manual script
- `visual_beats.json`: beats ที่แปลงจาก sections
- `visual_plan.json`: per-asset visual plan, stock keywords, AI fallback prompt
- `stock_query_report.json`: Pexels/Pixabay search attempts
- `cost_summary.json`: persisted estimated cost by trace run
- `state.json`: persisted episode state
- `final_unnormalized.mp4`: Remotion raw render ก่อน normalize
- `final.mp4`: final render ที่ upload path คาดหวัง

## Shorts

### Generate + Stream

- `POST /shorts/api/generate`
  - body ที่ใช้บ่อย:
    - `account_id` (required)
    - `topic` (optional)
    - `niche` (optional)
    - `language` (optional)
    - `mode` (`auto` | `step`)
  - response:
    - `{ "short_id": "short_YYYYMMDD_HHMMSS" }`

- `GET /shorts/api/stream/{short_id}` SSE
- `GET /shorts/api/episode/{short_id}` state ทั้งก้อน

### Control + Upload

- `POST /shorts/api/approve/{short_id}`
- `POST /shorts/api/cancel/{short_id}`
- `POST /shorts/api/upload/{short_id}`
  - ถ้า auth YouTube ไม่พร้อม จะได้ response แนว:
    - `manual_upload_recommended: true`

### Helpers

- `GET /shorts/api/accounts`
- `GET /shorts/api/youtube-auth-status`
- `GET /shorts/api/shorts`

## Settings + UI Assets

- `GET /api/settings/podcast`
- `POST /api/settings/podcast`
  - ใช้ persist system settings ที่ PodcastV2 UI ส่งผ่าน `system_settings`
- `GET /ui-assets/{filename}`
- `GET /static/{episode_id}/{filename}`
- `GET /shorts/static/{short_id}/{filename}`

## Common Error Patterns

- 400:
  - ขาด `topic` (non-script mode)
  - ขาด `raw_script` (script mode)
  - ขาด `account_id` (shorts)
  - upload ตอน auth ไม่พร้อม
- 404:
  - `episode_id` หรือ `short_id` ไม่พบ
  - `account_id` ไม่อยู่ใน cache
- 409:
  - resume ตอน episode กำลังรันอยู่
- PodcastV2:
  - manual script ไม่มี heading แบบ `## SECTION NAME` จะ fail ที่ format QC
  - render มี `final_unnormalized.mp4` แต่ไม่มี `final.mp4` แปลว่า normalize/render tail ยังไม่จบ
  - `cost_summary.json.status=error` ให้ดู `state.json.error` และ SSE/log step ที่ล้มก่อนสรุปว่า video ใช้งานได้

## Scope Note

- ไฟล์นี้เป็น quick reference สำหรับ runtime ปัจจุบัน
- ถ้าต้องย้อน rationale เชิงออกแบบ ให้เปิด `docs/superpowers/specs/*`
