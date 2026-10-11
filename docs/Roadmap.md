# Producer Mode Roadmap

## Supported direction

Keep MoneyPrinterV2 centered on a reviewable Thai documentary workflow:

1. Evidence-backed story and narration
2. Sequence-level visual direction and asset review
3. Thai narration and timing review
4. Revision-bound render preparation and explicit render authorization
5. Technical, visual, listening, and editorial acceptance of the final file

The canonical operating rules are in the installed `moneyprinter-producer-mode` skill and `docs/producer-mode-workflow.md`.

## Retained adjacent capability

The `moneyprinter-shorts-pack` skill uses the Remotion `ClipShort` composition to package approved source footage as a Short. It is a supporting skill, not a separate automated production dashboard.

TypeSafe asset review may provide advisory judgments. It cannot approve visual assets or replace producer review.

## Runtime boundary

- Producer Mode is run through `scripts/producer_mode.py` and `scripts/producer_review.py`.
- Documentary video uses Remotion `VideoPodcast`.
- `src/runtime_trace.py` records supported provider usage.
- The former Studio web server, automation APIs, scheduled jobs, and separate APOD pipeline are retired.

Historical design notes are retained under `docs/archive/` and `docs/superpowers/`; they are not the supported runtime or active backlog.
