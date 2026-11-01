import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from producer_palette_qc import measure, problems  # noqa: E402


def frames(rgb, n):
    return np.tile(np.array(rgb, np.float32).reshape(1, 1, 1, 3), (n, 9, 16, 1))


def test_saturated_deep_blue_with_bright_breaks_passes():
    deep = frames([0.02, 0.06, 0.2], 60)       # saturated deep blue, dark
    cream = frames([0.99, 0.89, 0.65], 10)     # bright scene
    m = measure(np.concatenate([deep, cream, deep]))
    assert m["dark_run"] == 60
    assert m["neutral_dark"] == 0
    assert problems(m) == []


def test_neutral_black_grey_and_long_dark_fail():
    black = frames([0.02, 0.02, 0.025], 100)
    grey = frames([0.4, 0.38, 0.36], 20)
    found = problems(measure(np.concatenate([black, grey])))
    assert any("saturation" in p for p in found)
    assert any("neutral black" in p for p in found)
    assert any("grey" in p for p in found)
    assert any("dark for 100 s" in p for p in found)


def test_skip_leaves_out_real_media():
    deep = frames([0.02, 0.06, 0.2], 30)
    photo = frames([0.4, 0.38, 0.36], 30)
    m = measure(np.concatenate([deep, photo]), skip=[(30, 60)])
    assert m["seconds"] == 30
    assert m["grey"] == 0
