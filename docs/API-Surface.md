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
  - รูปแบบ body ใกล้เคียง `/api/generate`
  - response:
    - `{ "episode_id": "podcast_v2_YYYYMMDD_HHMMSS" }`
- `GET /api/v2/stream/{episode_id}` SSE
- `GET /api/v2/episode/{episode_id}` state episode
- `POST /api/v2/upload/{episode_id}`
  - body: `privacy_status`, `publish_at`

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

## Scope Note

- ไฟล์นี้เป็น quick reference สำหรับ runtime ปัจจุบัน
- ถ้าต้องย้อน rationale เชิงออกแบบ ให้เปิด `docs/superpowers/specs/*`
