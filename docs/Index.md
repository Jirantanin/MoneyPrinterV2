# MoneyPrinterV2 Docs Index

เอกสารนี้เป็นจุดเริ่มต้นสำหรับการ navigate งานในโปรเจกต์
โดยเรียงลำดับจากภาพรวม -> การตั้งค่า -> รายละเอียดเชิงฟีเจอร์ -> เอกสารเก่า

## Start Here

1. [Roadmap](./Roadmap.md)
   - สรุปทิศทางโปรดักต์, runtime หลัก, สิ่งที่ shipped แล้ว, backlog
2. [QuickMap](./QuickMap.md)
   - แผนที่สั้นสำหรับเริ่มงานเร็ว, จุดเข้าโค้ด, API ที่ใช้บ่อย, และขอบเขต canonical/reference/archive
3. [Configuration](./Configuration.md)
   - อธิบายคีย์ใน `config.json`, provider, TTS/STT, upload, topic discovery
4. [API Surface](./API-Surface.md)
   - สรุป endpoint ที่ใช้จริง พร้อม request/response ที่จำเป็นต่อการ debug

## Runtime Entry Points

- `src/podcast_server.py`
  - FastAPI backend และ Studio runtime หลัก
- `src/podcast_ui.html`
  - หน้าจอ Studio ฝั่ง Web UI
- `src/main.py`
  - legacy launcher (ไม่ใช่เส้นทางหลัก)

## Feature Plans and Specs

โฟลเดอร์นี้เก็บเอกสารเชิงแผนและดีไซน์ของฟีเจอร์สำคัญ:

- `docs/superpowers/plans/`
  - แผนงานรายหัวข้อ (plan)
- `docs/superpowers/specs/`
  - เอกสารสเปกและดีไซน์ (spec/design)

ตัวอย่างไฟล์:
- `docs/superpowers/plans/2026-04-05-podcast-upgrade.md`
- `docs/superpowers/specs/2026-04-05-podcast-upgrade-design.md`
- `docs/superpowers/specs/2026-04-11-podcast-remotion-renderer-design.md`

## Archive (Reference Only)

- `docs/archive/`
  - เอกสารเก่าที่เก็บไว้เพื่ออ้างอิง ไม่ใช่แนวทาง runtime ปัจจุบัน
  - ตัวอย่าง: `AffiliateMarketing.md`, `TwitterBot.md`, `YouTube.md`

## Suggested Reading by Task

- เริ่มโปรเจกต์หรือ onboard คนใหม่:
  1. `docs/Index.md`
  2. `docs/Roadmap.md`
  3. `docs/Configuration.md`

- จะแก้ flow generation/render/upload:
  1. `docs/Roadmap.md`
  2. `docs/superpowers/specs/` ที่เกี่ยวข้อง
  3. ค่อยลงโค้ดใน `src/podcast_server.py` และ `src/classes/`

- ตรวจว่าอะไร legacy:
  1. `docs/archive/`
  2. `src/legacy/`
