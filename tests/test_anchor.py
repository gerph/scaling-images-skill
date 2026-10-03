import numpy as np
from PIL import Image

from scaling_images import canvas as cv
from scaling_images import geometry, seams
from scaling_images import state as st
from scaling_images.profiles import get_profile
from helpers import DESCRIPTION, make_job, run, save_result
from synth import FakeGenerator, ideal_image

GRID = ("--profile", "custom", "--tile", "512", "--min-pixels", "1")


def lum(a):
    return a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114


def test_anchor_restores_broad_colour_and_keeps_fine_detail():
    ideal = np.asarray(ideal_image((512, 512)))
    # A generator that lightened everything and tinted it blue.
    drifted = np.clip(ideal.astype(float) * [1.0, 1.1, 1.4] + 30, 0, 255).astype(np.uint8)
    anchored = seams.anchor_to_original(drifted, ideal, sigma=64)
    assert abs(lum(anchored).mean() - lum(ideal).mean()) < 0.03 * lum(ideal).mean()
    assert np.abs(anchored.astype(float).mean((0, 1)) - ideal.astype(float).mean((0, 1))).max() < 6
    # Pixel-scale detail is the generator's, not flattened to the original's blur.
    fine = lambda a: np.abs(np.diff(lum(a.astype(float)), axis=1)).mean()
    assert fine(anchored) > 0.6 * fine(drifted)


def test_anchor_of_a_faithful_tile_changes_almost_nothing():
    ideal = np.asarray(ideal_image((512, 512)))
    out = seams.anchor_to_original(ideal, ideal, sigma=64)
    assert np.abs(out.astype(int) - ideal.astype(int)).max() <= 2


def test_seam_correction_fades_with_distance():
    profile = get_profile("custom", tile=512, min_pixels=1)
    target = (1024, 1024)
    tiles = geometry.plan_grid(target, profile)
    ideal = ideal_image(target)
    source = ideal.resize((256, 256), Image.BOX)
    generator = FakeGenerator(ideal)
    canvas = cv.Canvas(target)
    cv.merge(canvas, tiles[0], np.asarray(generator.generate(tiles[0])))
    tile = tiles[1]
    supplied = np.asarray(cv.render_input(source, canvas, tile, (255, 0, 0), 6))
    returned = np.asarray(generator.generate(tile, tone=(1.0, 30)))
    ideal_window = np.asarray(generator.generate(tile)).astype(float)
    ux, _ = cv.unknown_origin(tile)

    def error_at(fixed, distance):
        x = ux + distance
        return float(np.abs(fixed[:, x:x + 8].astype(float) - ideal_window[:, x:x + 8]).mean())

    full = seams.tone_field(returned, supplied, tile)
    faded = seams.tone_field(returned, supplied, tile, decay=40)
    assert error_at(full, 200) < 2 and error_at(faded, 200) > 15      # far from the seam only the anchor helps
    assert error_at(faded, 2) < 6 < error_at(returned, 2)              # next to the seam it still mostly matches


def drifting_job(tmp_path, anchor, strength="1.0"):
    work, generator, ideal = make_job(tmp_path, size=(256, 256), factor=4,
                                      extra=GRID + ("--anchor", anchor, "--anchor-strength", strength))
    for _ in range(len(st.load(work)["tiles"])):
        tile = st.next_pending(st.load(work))
        # Every tile comes back a little lighter than the one before it.
        save_result(work, tile, generator.generate(tile, tone=(1.06, 6)))
        assert run("accept", "--work", work)[0] in (0, 5)
    return cv.Canvas.load(work).pixels, np.asarray(ideal)


def test_drift_adds_up_without_anchoring_and_not_with_it(tmp_path):
    for name in ("a", "b", "c"):
        (tmp_path / name).mkdir()
    off, ideal = drifting_job(tmp_path / "a", "off")
    on, _ = drifting_job(tmp_path / "b", "on")
    half, _ = drifting_job(tmp_path / "c", "on", "0.5")
    error = lambda canvas: abs(lum(canvas.astype(float)).mean() - lum(ideal.astype(float)).mean())
    assert error(on) < 4
    assert error(off) > 2 * error(on)
    # Half strength keeps some of the generator's lightening, but still bounds it well below no anchoring.
    assert error(on) <= error(half) < error(off)


def test_auto_is_off_when_restyling_and_option_is_recorded(tmp_path):
    path = str(tmp_path / "plain.png")
    ideal_image((256, 256)).save(path)
    import os
    work = str(tmp_path / "w")
    os.makedirs(work)
    open(os.path.join(work, "description.md"), "w").write(DESCRIPTION)
    assert run("init", path, "--factor", 4, "--restyle", "--work", work, *GRID)[0] == 0
    options = st.load(work)["options"]
    assert options["anchor"] == "auto" and options["restyle"] is True
    from scaling_images import commands
    assert commands._anchor_enabled(st.load(work)) is False
    state = st.load(work)
    state["options"]["restyle"] = False
    assert commands._anchor_enabled(state) is True
    state["options"]["anchor"] = "off"
    assert commands._anchor_enabled(state) is False
