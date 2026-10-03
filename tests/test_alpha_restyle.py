import os

import numpy as np
from PIL import Image

from scaling_images import canvas as cv
from scaling_images import state as st
from helpers import DESCRIPTION, run, save_result
from synth import FakeGenerator, ideal_image

GRID = ("--profile", "custom", "--tile", "512", "--min-pixels", "1")


def transparent_source(tmp_path, size=(256, 256), factor=4):
    """
    A disc of texture on a transparent background (with soft edges), plus the ideal enlargement.
    """
    target = (size[0] * factor, size[1] * factor)
    ideal = ideal_image(target)
    yy, xx = np.mgrid[0:size[1], 0:size[0]]
    radius = np.hypot(xx - size[0] / 2.0, yy - size[1] / 2.0)
    alpha = np.clip((size[0] * 0.4 - radius) / 3.0 + 0.5, 0, 1)
    small = np.asarray(ideal.resize(size, Image.BOX))
    rgba = np.dstack([small, (alpha * 255).astype(np.uint8)])
    # What a PNG exporter often leaves under transparent pixels.
    rgba[alpha == 0, :3] = 0
    path = str(tmp_path / "gem.png")
    Image.fromarray(rgba, "RGBA").save(path)
    work = str(tmp_path / "work")
    os.makedirs(work)
    open(os.path.join(work, "description.md"), "w").write(DESCRIPTION)
    return path, work, ideal, rgba


def test_init_asks_when_the_source_is_transparent(tmp_path):
    path, work, ideal, rgba = transparent_source(tmp_path)
    status, out, err = run("init", path, "--factor", 4, "--work", work, *GRID)
    assert status == 1
    assert "transparent" in err and "--alpha composite" in err and "--alpha keep" in err
    assert not os.path.exists(os.path.join(work, "state.json"))


def test_opaque_source_needs_no_alpha_option(tmp_path):
    path = str(tmp_path / "plain.png")
    ideal_image((256, 256)).save(path)
    work = str(tmp_path / "w")
    os.makedirs(work)
    open(os.path.join(work, "description.md"), "w").write(DESCRIPTION)
    assert run("init", path, "--factor", 4, "--work", work, *GRID)[0] == 0
    assert st.load(work)["alpha"]["mode"] is None


def test_composite_gives_an_opaque_result_on_the_chosen_colour(tmp_path):
    path, work, ideal, rgba = transparent_source(tmp_path)
    assert run("init", path, "--factor", 4, "--alpha", "composite", "--background", "#204080", "--work", work,
               *GRID)[0] == 0
    original = np.asarray(Image.open(os.path.join(work, "original.png")))
    assert tuple(original[0, 0]) == (0x20, 0x40, 0x80)       # transparent corner, not black
    assert not os.path.exists(os.path.join(work, "alpha.png"))
    assert st.load(work)["alpha"] == {"mode": "composite", "background": [32, 64, 128], "transparent": True}


def test_keep_restores_the_original_alpha_on_an_rgba_result(tmp_path):
    path, work, ideal, rgba = transparent_source(tmp_path)
    assert run("init", path, "--factor", 4, "--alpha", "keep", "--work", work, *GRID)[0] == 0
    original = np.asarray(Image.open(os.path.join(work, "original.png")))
    assert tuple(original[0, 0]) == (255, 255, 255)           # white backdrop, not black

    # The generator paints the disc over white: the ideal composited with the scaled-up alpha.
    alpha_big = np.asarray(Image.fromarray(rgba[..., 3]).resize((1024, 1024), Image.BICUBIC)) / 255.0
    painted = (np.asarray(ideal) * alpha_big[..., None] + 255 * (1 - alpha_big[..., None])).astype(np.uint8)
    generator = FakeGenerator(Image.fromarray(painted))
    for _ in range(len(st.load(work)["tiles"])):
        run("next", "--work", work)
        tile = st.next_pending(st.load(work))
        save_result(work, tile, generator.generate(tile))
        assert run("accept", "--work", work)[0] in (0, 5)
    output = str(tmp_path / "out.png")
    assert run("finish", "--work", work, "--output", output)[0] == 0

    final = np.asarray(Image.open(output))
    assert final.shape == (1024, 1024, 4)
    assert abs(final[..., 3].astype(int) - np.round(alpha_big * 255)).max() <= 1
    inside = alpha_big > 0.999
    assert np.abs(final[..., :3][inside].astype(int) - np.asarray(ideal)[inside].astype(int)).max() <= 2
    # Edge pixels lose the white halo: composited on black they are not lighter than the true colour.
    edge = (alpha_big > 0.3) & (alpha_big < 0.7)
    assert np.abs(final[..., :3][edge].astype(int) - np.asarray(ideal)[edge].astype(int)).mean() < 6


def test_instructions_mention_the_plain_backdrop(tmp_path):
    path, work, ideal, rgba = transparent_source(tmp_path)
    run("init", path, "--factor", 4, "--alpha", "keep", "--background", "grey", "--work", work, *GRID)
    status, out, err = run("next", "--work", work)
    assert "plain grey backdrop" in out and "Keep it perfectly flat" in out


def test_restyle_changes_the_instructions_and_turns_off_the_structure_check(tmp_path):
    path = str(tmp_path / "plain.png")
    ideal_image((256, 256)).save(path)
    work = str(tmp_path / "w")
    os.makedirs(work)
    open(os.path.join(work, "description.md"), "w").write(DESCRIPTION)
    assert run("init", path, "--factor", 4, "--restyle", "--work", work, *GRID)[0] == 0
    options = st.load(work)["options"]
    assert options["restyle"] is True and options["structure"] is False
    status, out, err = run("next", "--work", work)
    assert "TARGET STYLE" in out and "Do not copy how the original is rendered" in out
    assert "keep the palette of the original" in out
    assert "do not make it more vivid" not in out
    assert "do not turn it into smooth colour" not in out
    # Still forbidden in a restyle:
    assert "Keep the exact framing" in out and "lies outside this tile" in out
