# Producer Mode Mars Long-Form Render: Render Input And QC Post-Mortem

- Date: 2026-05-25
- Scope: long-form Thai episode, `podcast_v2_mars-civilization-3-7-billion-years_20260525_102807`
- Final output: `.mp/podcast_v2_mars-civilization-3-7-billion-years_20260525_102807/final.mp4`
- Final result: `pass`, 963.1 seconds, 1920x1080, H.264 + AAC

## Summary

ระหว่างเตรียม render input หลังได้รับอนุญาตให้เรนเดอร์ พบว่า Thai overlay labels ใน `render_props.json` กลายเป็น `?` และ chapter overlays ที่ควรว่างกลับแสดง fallback ชื่อ `Scene N` จึงหยุดก่อนเริ่ม video render แล้วแก้ renderer-facing artifacts ก่อน

หลังเรนเดอร์เสร็จ `final-qc` รอบแรกยังไม่ผ่านการส่งมอบ เพราะ manifest บางรายการขาด provenance ที่ QC ตรวจได้ จึงเติมข้อมูลแหล่งที่มา/ที่มาของกราฟิกอย่างตรงไปตรงมา แล้วรัน QC ใหม่จนผ่าน พร้อมตรวจภาพตัวอย่างและ decode check

การแก้รอบนี้เป็น artifact-level fix สำหรับตอนนี้และการปรับ producer skill ไม่ใช่ source-code fix ของ renderer/preflight

## Record Preconditions

เอกสารนี้เขียนหลังมีหลักฐานครบ:

- Reproduction: การเตรียม props แบบ no-render ทำให้เห็น `?` ใน label และ `Scene N` ใน title ก่อนเกิด video render
- Root cause: ระบุตำแหน่งความเสียหายได้ว่าเกิดก่อน Remotion และระบุ fallback title จาก `producer_render_preflight._safe_title()` ได้
- Fix: สร้าง label/title props ใหม่อย่างควบคุมได้ และเติม provenance สำหรับ assets ที่ใช้งานจริง
- Validation: final technical QC และ visual QC ผ่านบนไฟล์ render สุดท้าย

## Symptoms

1. `render_overlay_labels.json` และ `render_props.json` มีภาษาไทยเป็นเครื่องหมาย `?` แม้ข้อความ narration หลักยังอ่านได้
2. Scene ที่จงใจไม่ต้องมี chapter title ถูก preflight เติมชื่อ `Scene 2`, `Scene 3`, ... เอง
3. Editorial asset manifest ที่ผ่านการคัดภาพแล้วไม่ตรง contract ของ renderer: สถานะ `approved_inspected` และไม่มี `asset_index`
4. คลิป NASA ที่ต้องเล่นต่อเนื่องถูกวางเป็นหลาย slot ซึ่งถ้าใช้ตรง ๆ จะเริ่มคลิปใหม่ซ้ำแต่ละช่วง
5. หลัง render สำเร็จ `final-qc` ขึ้น review เพราะ assets 13 รายการขาด source หรือ prompt provenance ที่ระบบตรวจรับได้
6. Cost report ของ full pass ไม่นับ TTS sample ที่สร้างแบบจ่ายเงินจริงแล้วนำกลับมา reuse ในรอบเต็ม

## Root Causes

### 1. Thai Labels Corrupted Before Render

ข้อความภาษาไทยแบบ literal ถูกฝังใน Python source ที่ส่งผ่าน PowerShell ระหว่างสร้าง render artifacts ทำให้อักขระสูญหายก่อน serialize เป็น JSON ความเสียหายจึงไม่ได้เกิดใน Remotion หรือในวิดีโอ encoder

หลักฐาน:

- `render_input_debug_ledger.json` ระบุว่า label artifact เสียตั้งแต่ก่อน Remotion
- Unicode escape probe ที่ใช้ source แบบ ASCII-only สร้างข้อความไทยที่อ่านได้
- `render_script.json` ที่ไม่ได้ผ่านทางเดียวกับ label constants ยังเก็บข้อความที่ตั้งใจไว้ได้

### 2. Blank Chapter Titles Were Not A Supported Intent

`src/producer_render_preflight.py::_safe_title(scene, fallback)` เติม fallback `Scene N` เมื่อ `scene_title` และ `section_title` ว่าง ดังนั้นการล้าง title ใน editorial script ไม่ได้แปลว่า overlay จะถูกปิด

### 3. Editorial Approval Was Not The Renderer Contract

Manifest สำหรับตัดสินใจเชิงบรรณาธิการเก็บสถานะและ timeline ที่ละเอียดกว่าที่ native renderer รับได้ ขณะที่ preflight รับ asset statuses เฉพาะ `downloaded`, `generated`, `skipped_existing` และใช้ `asset_index` เพื่อจัดลำดับ การไม่มี bridge step ทำให้ cut ที่อนุมัติแล้วเสี่ยงถูก render คนละแบบ

### 4. Provenance Was Reviewed Conceptually But Not Against QC Fields

กราฟิกที่สร้างเอง, ภาพ reframe, และ media ที่สืบทอดมาจาก official source มีเหตุผลการเลือกภาพแล้ว แต่ไม่มี `source_url`, `download_url`, หรือ `prompt`/provenance note ใน field ที่ `final-qc` ตรวจ จึงถูกแจ้งขาด provenance ตอนท้าย

## Fix Applied In This Episode

1. สร้าง Thai overlay labels ใหม่จาก stable mapping โดยใช้ Unicode escapes ใน source ที่ต้องวิ่งผ่าน shell แล้วตรวจว่าไม่มี `?` ใน props
2. Override `props_preview.sceneTitles` จาก title ที่ตั้งใจจริง ให้เหลือ title ที่ไม่ว่างเพียง 7 section เท่านั้น
3. แยก renderer-facing artifacts ออกจาก editorial artifacts:
   - `render_asset_manifest.json`
   - `render_visual_timeline.json`
   - `render_preflight.json`
   - `render_props_preview.json`
   - `render_props.json`
4. ทำ excerpt ของ NASA wet-to-dry visualization ให้เล่นต่อเนื่องแทนการ restart คลิปเดิมเป็นช่วงสั้นซ้ำ ๆ
5. เติม provenance ที่ซื่อสัตย์ให้ official images, derived reframes, local graphics และ visualization excerpts ใน manifest ที่เกี่ยวข้อง
6. เพิ่ม `cost_reconciliation.json` ให้รวมค่า TTS sample ที่จ่ายแล้วแต่ถูก reuse ใน full pass

## Validation

- `render_input_debug_ledger.json`: status `fixed_before_video_render`
- `visual_qc.json`: status `pass`, ตรวจภาพตัวอย่าง 13 ตำแหน่ง รวม chapter titles, Thai labels, NASA reconstruction disclaimer และ outro
- `final_qc.json`: status `pass`, warnings/errors ว่าง, provenance missing `0` entries
- `final.mp4`: 963.1 seconds, 548,735,593 bytes, 1920x1080, 25 fps, มีทั้ง video/audio streams
- Decode check ของไฟล์สุดท้ายผ่านก่อนส่งมอบ

## What We Learned

| Lesson | Change Required In Producer Workflow |
| --- | --- |
| การอนุมัติภาพยังไม่เท่ากับการอนุมัติ render input | ต้องมี renderer-contract bridge และ inspect props แบบ no-render |
| Text ไทยอาจเสียก่อนถึง renderer | ต้อง assert ข้อความภาษาไทยใน JSON/props และใช้ UTF-8 file input หรือ Unicode escapes เมื่อผ่าน shell |
| Blank title อาจกลายเป็น overlay fallback | ต้อง assert จำนวน/ข้อความ chapter titles ที่จะขึ้นจอจริง |
| Provenance ที่คนอ่านเข้าใจอาจไม่ผ่าน machine QC | ต้องตรวจ field provenance ตาม contract ก่อน render |
| วิดีโอเดียวกันที่แบ่ง slot ไม่ได้แปลว่าจะเล่นต่อเนื่อง | ต้องสร้าง continuous excerpt หรือรองรับ in/out points อย่างชัดเจน |
| ค่า sample ที่ reuse ไม่ใช่ค่าใช้จ่ายศูนย์ | ต้องทำ session cost reconciliation ใน handoff |

## Skill Changes From This Incident

`moneyprinter-producer-mode` ควรบังคับขั้นตอนต่อไปนี้:

1. สร้างและตรวจ renderer-facing bridge artifacts ก่อนใช้สิทธิ์ render
2. ตรวจ Thai text corruption, unintended title fallback และ provenance completeness ใน props/manifest ก่อนยิง video render
3. แยก editorial manifest ออกจาก renderer-compatible manifest อย่างชัดเจน
4. บังคับ continuous playback rule สำหรับ footage/excerpt ที่ต้องเล่าเหตุการณ์ต่อเนื่อง
5. เก็บ cost reconciliation เมื่อทำ paid sample แล้ว reuse
6. ระหว่าง render งานยาว ให้ monitor process/log/artifact จริงและอย่าเชื่อ ETA แรกทันที

## Known Follow-Ups

รายการนี้ยังไม่ได้แก้ใน product source code รอบนี้:

1. เพิ่มทางเลือกใน `producer_render_preflight` ให้ blank title หมายถึงไม่แสดง overlay ได้จริง แทนการต้อง override artifact หลัง preflight
2. สร้าง bridge command ที่แปลง editorial manifest/timeline เป็น renderer contract พร้อม assertions โดยอัตโนมัติ
3. ตรวจและทำให้ `producer_broll_expander.py` เป็น topic-neutral ก่อนใช้กับเรื่องนอกโดเมนเดิม โดยเฉพาะกฎ relevance/block ที่อาจชนคำว่า Mars/Martian
4. รวม paid sample reuse เข้า cost reporting หลักโดยไม่ต้องทำ reconciliation แยกด้วยมือ
5. วัดประสิทธิภาพ render/concurrency บนงานยาวก่อนตัดสินใจปรับค่ารันไทม์

## Post-Delivery Viewer Review

หลังดูไฟล์ส่งมอบ นนให้ feedback เพิ่มเติมที่กระทบมาตรฐานการตัดต่อโดยตรง:

1. การเปลี่ยน visual แล้วกลับมาเห็นภาพเดิมรู้สึกไม่มีเหตุผลเชิงเรื่องเล่า
2. Graphic ที่มีข้อความอ่านยากเมื่อถูก pan ซ้าย/ขวา
3. Directional slide transitions ดูเป็น template มากกว่า documentary ขณะที่ fade ที่มีอยู่ดูเหมาะกว่า

การตรวจ timeline ยืนยันว่ามี consecutive repeated-asset runs 26 ช่วงใน render revision นี้ โดยมี transition ระหว่าง still เดิมที่ component รวมทิ้งได้ 106 จุด และมีอีก 5 จุดที่ซ้ำข้าม scene boundary ซึ่งต้องแก้ใน timeline ก่อน render revision ใหม่ ไม่พบรูปแบบ `A -> B -> A` แบบติดกันทันที นอกจากนี้ `VideoPodcast` ใช้ motion cycle กับ stills โดยไม่รู้ว่า asset เป็น graphic ที่ต้องรักษาความอ่านง่าย

แนวแก้สำหรับวิดีโอถัดไป:

- merge still เดิมที่อยู่ติดกันเป็น hold/motion ต่อเนื่อง ไม่วาง transition บนภาพเดิม และตรวจรูปแบบ `A -> B -> A` ก่อน render;
- ใช้ static หรือ subtle centered scale สำหรับ text-heavy graphics; ไม่ใช้ pan แนวนอน/แนวตั้งกับข้อมูลที่ต้องอ่าน;
- ใช้ fade/dissolve เป็น transition หลักของ long-form documentary และใช้ hard cut เฉพาะจังหวะเปรียบเทียบหรือย้ำประเด็น;
- ปรับ `VideoPodcast` ให้ใช้ documentary-readable motion profile, fade ระหว่าง scenes และ compact ภาพเดิมที่ต่อกันทั้งภายใน scene และข้าม scene ที่ไม่มี chapter title โดยไม่กระทบ `VideoShort`.

## Authorized Revision Render Timeout Incident

- Revision: `podcast_v2_mars-civilization-3-7-billion-years_20260525_102807_revision_viewer-feedback_01`
- Symptom: authorized full render stopped at frame `16241` with `Timeout (30000ms) exceeded rendering the component at frame 16241`.
- Failed beat: `S05B04-R02`, graphic asset `assets/graphics_png/S06B03_evidence_balance.png` at `649.64` seconds.
- Disproof: the PNG decoded correctly; the exact failed frame rendered in `9.994` seconds with the original `30000ms` limit; frames `16220-16260` rendered in `14.127` seconds with the same limit and concurrency.
- Supported cause: a transient stall during the long Remotion run exceeded the implicit per-frame default timeout, rather than a deterministically broken asset or local sequence.
- Fix: `src/producer_renderer.py` now passes an explicit Remotion `--timeout=120000` for Producer Mode video renders.
- Evidence ledger: revision-local `render_input_debug_ledger.json`.
- Validation: the authorized rerender completed, crossed frame `16241`, produced a `963.1` second `final.mp4`, and passed technical QC, full-file decode check, and representative visual QC.
