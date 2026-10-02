import json

import pytest
from PIL import Image

from scaling_images import description as d

SAMPLE = """# Style
Photograph, soft focus.

```json
{"content": [
  {"name": "left kitten", "note": "ginger", "box": [0.1, 0.4, 0.4, 0.8]},
  {"name": "hills", "note": "distant", "box": [0.0, 0.2, 1.0, 0.4]},
  {"name": "wall", "note": "foreground", "box": [0.0, 0.8, 0.2, 1.0]}
]}
```
"""


def write(tmp_path, text):
    path = tmp_path / "description.md"
    path.write_text(text)
    return str(path)


def test_load_sample(tmp_path):
    prose, items, text = d.load(write(tmp_path, SAMPLE))
    assert "Photograph" in prose and "json" not in prose
    assert [i["name"] for i in items] == ["left kitten", "hills", "wall"]


def test_errors(tmp_path):
    with pytest.raises(d.DescriptionError):
        d.load(write(tmp_path, ""))
    with pytest.raises(d.DescriptionError):
        d.load(write(tmp_path, "just prose"))
    bad = SAMPLE.replace("0.4, 0.8]", "1.4, 0.8]")
    with pytest.raises(d.DescriptionError):
        d.load(write(tmp_path, bad))


def test_hash_ignores_trailing_space_and_line_endings_but_not_words():
    base = d.description_hash(SAMPLE)
    assert d.description_hash(SAMPLE.replace("\n", "  \r\n")) == base
    assert d.description_hash(SAMPLE.replace("soft", "hard")) != base


def test_classify(tmp_path):
    import numpy as np
    from scaling_images import geometry
    from scaling_images.profiles import get_profile
    _, items, _ = d.load(write(tmp_path, SAMPLE))
    tiles = geometry.plan_grid((2560, 1920), get_profile("gpt-image-2-api"))
    mask = np.zeros((1920, 2560), dtype=bool)
    mask[:, :1280] = True

    # First tile (accepted 0-1280): left kitten (x 256-1024) and wall are new.
    ctx, new, out = d.classify(items, tiles[0], (2560, 1920))
    assert {i["name"] for i, _ in new} == {"left kitten", "hills", "wall"}

    # Second tile: hills straddle the seam so are new and continue; kitten is in context.
    ctx, new, out = d.classify(items, tiles[1], (2560, 1920), mask)
    assert [i["name"] for i, c in new] == ["hills"] and new[0][1] is True
    assert {i["name"] for i, _ in ctx} == {"left kitten"}
    # The wall (x 0-512) is left of the window, which starts at 512.
    assert [i["name"] for i, _ in out] == ["wall"]


def test_overlay(tmp_path):
    _, items, _ = d.load(write(tmp_path, SAMPLE))
    image = d.overlay(Image.new("RGB", (200, 100)), items)
    assert image.size == (200, 100)
