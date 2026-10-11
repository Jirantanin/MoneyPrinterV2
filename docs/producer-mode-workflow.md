# Producer Mode: evidence, sequence direction and revision-bound delivery

Producer Mode now checks the story and its evidence before committing to final media production. Source IDs alone no longer produce a passing fact-check. Script length uses one explicit Thai Unicode contract, screen-time exposure comes from selected render slots, and final technical checks do not imply creative acceptance.

The installed skill is `C:/Users/66984/.codex/skills/moneyprinter-producer-mode/SKILL.md`. It is outside this Git repository; changes to it require separate distribution/backup. Its references cover evidence review, sequence/listening review, artifact contracts and the render bridge.

## Changes

| Review concern | Implementation |
| --- | --- |
| Sources mistaken for proof | `producer_contract.claim_report` separates mapped/verified/uncertain/unsupported, requires attributed source passages and current script identity; arbitrary fallback source assignment removed |
| Story development too weak | Skill adds angle selection, opening/ending test, section cut test, separate truth/story/spoken-Thai passes; production requires a current editorial review including claim extraction coverage |
| Conflicting length targets | plan `episode_spec` is canonical; writer, expansion review, skill helper and production/render checks use `producer_contract` |
| Beat-local asset choices | Skill directs whole sequences first, batches candidates and approves each placement; speech-map verification precedes timeline lock |
| Slot ratios hide exposure | `visual_policy.time_exposure` reports actual assigned seconds, section ratios and longest graphic run; preflight recomputes on selected props and resolves warnings only with current sequence review |
| Technical QC mistaken for acceptance | Full ffmpeg decode plus distinct visual/listening/editorial evidence tied to final SHA256; missing/stale creative review leaves status review |
| Repeated rules and render permission friction | Shorter skill with routed references; explicit natural-language consent tied to prepared content fingerprint; initial attempt plus two unchanged-input technical retries |

`expand-script` previously appended Moon-specific paragraphs based on generic beat IDs. It now preserves narration and reports that evidence-backed editorial revision is required. It never pads another topic to a target count.

## New episode or migration of a working copy

1. Initialize a new plan with the existing `producer_mode.py init` command, or make a separate working copy of the chosen source episode. Never mass-migrate archived outputs.
2. Confirm `episode_spec`: default long-form uses 5,500–8,000 narration-only U+0E00–U+0E7F characters; explicit user overrides live here. Legacy nonspace targets are not equivalent. Test cuts are exempt from the character band, but any explicitly requested audio minimum still applies.
3. Develop the editorial core and narration, then extract substantive key_claims and map sources. Use `producer_review.py scaffold --plan ...` for pending review records. Inspect actual sources, fill evidence and editorial observations, and merge reviewed fields into the working plan. The scaffold never approves or rewrites the plan.
4. Run `producer_review.py check --plan ...`. Actual `produce-assets` and `produce-tts` checkpoints reject missing/currently invalid reviews before provider calls. Dry runs remain available.
5. Produce/review narration, speech timing, visual sequences and selected assets. Use `render-preflight` to inspect renderer slots and exposure. For review warnings, record sequence_review.json with the emitted render_slots_revision, status, reviewer, reviewed_at, decisions and unresolved_issues.
6. Run `producer_review.py prepare --plan ...`. This creates local prepared audio/props and a revision fingerprint without video rendering. Inspect that concrete mix and sequence before asking for user render consent.
7. After actual consent, record it with `producer_review.py authorize --plan ... --user-message "actual explicit consent"`, then use `producer_mode.py render-video`. Planning approval and --force cannot bypass this gate. Do not fabricate consent or reset counters by recording the same message again.
8. Run final-qc and supply actual observations in visual_qc.json, listening_qc.json and editorial_qc.json, referencing the final file hash. Write public copy in `seo_packaging` (titles, `upload_description`, `description_source_ids`, tags, hashtags, pinned comment), run `upload-pack`, then inspect the generated files before delivery. Publishing remains a separate user action: on explicit user direction, `scripts/youtube_upload.py` (`request` → `upload` → `status`, `schedule`, `reconnect`) uploads `final.mp4` privately or with a scheduled `publishAt` and writes receipts in `upload_pack/`.

The claim validator checks recorded evidence structure and freshness, not whether the claim is true. The producer must read the evidence. Similarly, creative review records attest to real viewing/listening; a machine check cannot replace those acts. A non-factual transition can use `non_factual: true` only after review; claim_coverage_review must account for all such scenes.

## Compatibility audit and validation (2026-09-18)

- 28 offline regression/integration tests passed, including existing b-roll and upload-pack tests.
- An integration fixture prepared actual local WAV audio and props, recorded fixture-only authorization and verified that the video renderer was never called.
- Changed media at the same path, changed props and exhausted retry limits invalidate permission. Unapproved --force leaves an existing final untouched.
- The skill validator passed; linked references and Thai Unicode were checked. The duration helper CLI counted exactly 5,500 Thai characters despite extra ASCII content.
- Studio ASGI smoke tests returned 200 for `/` and `/api/episodes`. Producer Mode has a CLI workflow; no new HTTP endpoint was added.
- Local provider preflight failed because Ollama at 127.0.0.1:11434 was unreachable. No paid generation or full episode render was performed.
- Read-only same-script audit of `podcast_v2_tno-remember-past_20260917`: the previous report called 60 source-mapped claims pass; the new report correctly records 60 mapped and zero recorded verified reviews. This does **not** establish that those claims are false. Its 9,431 Thai characters exceed the default range; using it again requires an explicit episode scope decision and current reviews. Original plan/script hashes were unchanged.

This is contract/runtime-preparation evidence, not proof of greater audience retention. A creative before/after episode comparison remains a production exercise requiring the episode's generation budget and final render authorization.

## Implementation test ledger

- Initial suite: 24 passed, one preflight failure. PDB showed the new policy result was computed correctly but the returned report still referenced a removed cached-review variable. Returning the current sequence-review artifact fixed the failure; the 25-test suite passed.
- Added command-path preparation/provider-gate tests. The first integration fixture had 8 kHz six-second PCM below the existing 100 KB merged-audio threshold. A representative 24 kHz fixture exercised the existing renderer contract; 28 tests passed. No production threshold was weakened.

Existing uncommitted work was retained. Before-edit copies of the touched existing modules and installed skill were saved under `C:/Users/66984/AppData/Local/Temp/moneyprinter-producer-v2-20260918-182610`.
