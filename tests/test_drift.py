import numpy as np
from PIL import Image

from scaling_images import seams
from scaling_images import state as st
from helpers import make_job, run, save_result
from synth import ideal_image

GRID = ("--profile", "custom", "--tile", "512", "--min-pixels", "1")


def test_faithful_region_is_not_flagged_and_lighter_one_is():
    ideal = ideal_image((512, 512))
    source = np.asarray(ideal.resize((128, 128), Image.BOX))
    pixels = np.asarray(ideal)
    ok = seams.colour_drift(pixels, source, (512, 512), (0, 0, 512, 512))
    assert not ok["flagged"] and 0.97 < ok["lightness"] < 1.03

    lighter = np.clip(pixels.astype(float) * 1.3 + 10, 0, 255).astype(np.uint8)
    bad = seams.colour_drift(lighter, source, (512, 512), (0, 0, 512, 512))
    assert bad["flagged"] and bad["lightness"] > 1.25
    assert any("lightness" in reason for reason in bad["reasons"])


def test_blue_cast_is_reported_by_channel():
    ideal = ideal_image((512, 512))
    source = np.asarray(ideal.resize((128, 128), Image.BOX))
    cast = np.asarray(ideal).astype(float)
    cast[..., 2] = cast[..., 2] * 1.5 + 20
    drift = seams.colour_drift(np.clip(cast, 0, 255).astype(np.uint8), source, (512, 512), (0, 0, 512, 512))
    assert drift["flagged"] and any("blue" in reason for reason in drift["reasons"])


def test_near_black_region_is_not_flagged_on_a_noisy_ratio():
    source = np.full((64, 64, 3), 6, dtype=np.uint8)
    pixels = np.full((256, 256, 3), 14, dtype=np.uint8)       # 2.3x, but only 8 grey levels
    assert not seams.colour_drift(pixels, source, (256, 256), (0, 0, 256, 256))["flagged"]


def test_accept_warns_about_drift_and_preview_shows_a_table(tmp_path):
    work, generator, ideal = make_job(tmp_path, size=(256, 256), factor=4, extra=GRID + ("--anchor", "off"))
    for _ in range(2):
        tile = st.next_pending(st.load(work))
        save_result(work, tile, generator.generate(tile, tone=(1.5, 30)))
        status, out, err = run("accept", "--work", work)
    assert status == 5 and "colour has drifted" in out and "lightness" in out
    status, out, err = run("preview", "--work", work)
    assert "Lightness against the original" in out and "row 0:" in out and "*" in out
    assert "Drifted tiles:" in out


def test_anchoring_keeps_the_same_generator_from_being_flagged(tmp_path):
    work, generator, ideal = make_job(tmp_path, size=(256, 256), factor=4, extra=GRID)
    tile = st.next_pending(st.load(work))
    save_result(work, tile, generator.generate(tile, tone=(1.5, 30)))
    status, out, err = run("accept", "--work", work)
    assert "colour has drifted" not in out
    status, out, err = run("preview", "--work", work)
    assert "Drifted tiles:" not in out
