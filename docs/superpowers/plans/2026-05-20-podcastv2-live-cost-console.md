# PodcastV2 Live Cost Console Plan

## Goal

Make the existing PodcastV2 Cost Estimate panel feel live during asset generation.
The user should see the estimated total rise gradually as paid provider calls finish,
without changing the main Studio layout or taking space from video preview and logs.

## Placement

Use the existing Cost Estimate card in the left column, below the pipeline steps.
Do not add a large new dashboard surface. The available space is narrow and tall, so
the design should be compact, scannable, and calm.

## Recommended UI

### Header

- Keep the title: `COST ESTIMATE`.
- Status pill on the right: `WAITING`, `RUNNING`, `FINAL`, or `ERROR`.
- Use `Estimated` wording because some providers are calculated from rate-card units,
  not direct invoice values.

### Total

- Large USD total, for example `$0.0842`.
- Small THB estimate beside or below it, for example `~THB 3.08`.
- Animate the number with a short count-up when the total changes.

### Latest Delta

Show a compact one-line tick under the total:

```text
+$0.0038 FLUX - scene 16 asset 3
```

Use a soft cyan/green accent. The delta may briefly pulse, but should not distract from
the pipeline.

### Provider Breakdown

Use five compact rows with mini bars:

```text
Claude       $0.0182  [#######---]
Gemini TTS   $0.0310  [#########-]
Gemini Img   $0.0390  [##########]
FLUX         $0.0152  [####------]
Stock        $0.0000  [----------]
```

Rows should be sorted by cost descending or keep a stable provider order. Stable order
is calmer; cost-descending is better for diagnostics. Prefer stable order first.

### Latest Activity

Show the latest 3-5 cost ticks only:

```text
FLUX fallback - scene 16 asset 3   +$0.0038
FLUX fallback - scene 16 asset 2   +$0.0038
Gemini anchor - scene 16           +$0.0390
```

No full event log here. The existing Pipeline Logs panel already handles verbose text.

### Scene Summary

Do not add a full 1-32 scene strip in the first pass; it will be cramped.
Use one compact line instead:

```text
Scene 17/32 - paid assets 46
```

## Backend Event Design

Emit live cost snapshots over the existing SSE stream during generation.

Use snapshot-first events, not only deltas, so reconnects or duplicate events cannot
double-count cost on the frontend.

Example:

```json
{
  "type": "cost_summary",
  "status": "running",
  "estimated_cost": {
    "run_id": "podcast_v2_...",
    "cost_usd": 0.0842,
    "provider_breakdown": {}
  },
  "last_cost_event": {
    "provider": "runware_flux1_image",
    "scene": 16,
    "asset": 3,
    "delta_usd": 0.0038,
    "label": "FLUX fallback image"
  }
}
```

## Backend Trigger Points

Send a live cost update after paid or tracked provider usage is appended:

- TTS scene completion.
- Gemini anchor image completion.
- Pexels/Pixabay stock result, even when cost is zero.
- Runware/FLUX fallback completion.
- Kling completion if a rate is available.
- Final pipeline completion or error.

## Throttling

For the first pass, emit immediately after paid calls because asset generation is not
extremely high frequency. If the UI becomes noisy, add a 1-2 second throttle while still
sending final summaries immediately.

## Implementation Notes

- Keep one trace `run_id` across the whole PodcastV2 pipeline.
- Continue using `append_api_usage(...)` for non-LLM providers.
- Continue using `summarize_run_cost(run_id)` for snapshot totals.
- Add enough metadata to usage or event context to identify scene, asset, and provider.
- Avoid frontend-only cost math for totals; frontend should render backend snapshots.
- Frontend may animate display values, but the source of truth is backend `cost_usd`.

## First Pass Checklist

- [ ] Add a helper that pushes `cost_summary` SSE snapshots from backend.
- [ ] Add `last_cost_event` metadata for asset-stage provider calls.
- [ ] Update the Cost Estimate card into the compact live console.
- [ ] Add count-up animation for total changes.
- [ ] Add provider mini bars.
- [ ] Add latest activity list with the most recent 3-5 ticks.
- [ ] Keep a final snapshot persisted to episode state and `cost_summary.json`.
- [ ] Smoke-test with a mock run or short episode and verify no double-counting.

## Explicit Non-Goals For First Pass

- No large new dashboard layout.
- No full scene strip unless there is room later.
- No billing-grade promise; label values as estimates.
- No changes while a production generation is running.
