"""Colour QC for a rendered episode: saturation, neutral blacks, grey graphics and dark stretches.

Thresholds come from three Kurzgesagt teardowns against our last four episodes (นน 2026-11-01,
research_notes/teardown_kurz_compare_palette/SCENE_DESIGN.md). Frames are float RGB in 0..1, one per second.
"""
from __future__ import annotations

import numpy as np

LIMITS = {
    "sat_min": 0.72,        # mean saturation of the graphics
    "neutral_dark_max": 0.08,  # share of pixels that are dark and unsaturated (neutral black)
    "grey_max": 0.05,       # share of mid-value pixels with almost no colour (grey / brown haze)
    "dark_run_max": 90,     # longest run of seconds whose mean luminance stays under 0.3
}


def frame_stats(f: np.ndarray) -> dict:
    mx, mn = f.max(-1), f.min(-1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    lum = 0.2126 * f[..., 0] + 0.7152 * f[..., 1] + 0.0722 * f[..., 2]
    return {"lum": float(lum.mean()), "sat": float(sat.mean()),
            "neutral_dark": float(((lum < 0.12) & (sat < 0.45)).mean()),
            "grey": float(((lum >= 0.12) & (lum <= 0.85) & (sat < 0.2)).mean())}


def measure(frames: np.ndarray, skip: list[tuple[float, float]] = ()) -> dict:
    """frames: (N, H, W, 3) at 1 fps from t=0; skip: (start, end) seconds of real media to leave out."""
    keep = [i for i in range(len(frames)) if not any(a <= i < b for a, b in skip)]
    per = [frame_stats(frames[i]) for i in keep]
    run = best = 0
    for i, s in zip(keep, per):
        run = run + 1 if s["lum"] < 0.3 else 0
        best = max(best, run)
    mean = lambda k: float(np.mean([s[k] for s in per])) if per else 0.0  # noqa: E731
    return {"seconds": len(per), "sat": mean("sat"), "lum": mean("lum"), "neutral_dark": mean("neutral_dark"),
            "grey": mean("grey"), "dark_run": best}


def problems(m: dict, limits: dict = LIMITS) -> list[str]:
    out = []
    if m["sat"] < limits["sat_min"]:
        out.append(f"saturation {m['sat']:.2f} < {limits['sat_min']}: push colours, drop grey haze and neutral shadows")
    if m["neutral_dark"] > limits["neutral_dark_max"]:
        out.append(f"neutral black {m['neutral_dark']:.0%} > {limits['neutral_dark_max']:.0%}: shadows and vignette "
                   "should be the scene's saturated deep colour, not black")
    if m["grey"] > limits["grey_max"]:
        out.append(f"grey/brown {m['grey']:.0%} > {limits['grey_max']:.0%} of pixels")
    if m["dark_run"] > limits["dark_run_max"]:
        out.append(f"dark for {m['dark_run']} s in a row > {limits['dark_run_max']} s: add a bright scene")
    return out
