import numpy as np
from PIL import Image

from scaling_images import canvas as cv
from scaling_images import geometry
from scaling_images import state as st
from scaling_images.profiles import get_profile
from helpers import DESCRIPTION, make_job, run
from synth import ideal_image


def hard_edged_source():
    """
    A small image with a diagonal hard edge, which a nearest-neighbour enlargement turns into a staircase.
    """
    yy, xx = np.mgrid[0:128, 0:128]
    flat = np.where(xx + yy > 128, 200, 40).astype(np.uint8)
    return Image.fromarray(np.dstack([flat, flat, flat]))


def test_smooth_input_has_no_staircase_but_nearest_does():
    source = hard_edged_source()
    tile = geometry.plan_grid((512, 512), get_profile("custom", tile=512, min_pixels=1))[0]
    canvas = cv.Canvas((512, 512))
    nearest = np.asarray(cv.render_input(source, canvas, tile, (255, 0, 0), 6, "nearest")).astype(float)[..., 0]
    smooth = np.asarray(cv.render_input(source, canvas, tile, (255, 0, 0), 6, "smooth")).astype(float)[..., 0]

    def sharpest_step(a):
        # A staircase edge changes by the full contrast in one pixel; a smooth ramp spreads it out.
        return float(np.abs(np.diff(a[256, 200:320])).max())

    assert sharpest_step(nearest) > 150
    assert sharpest_step(smooth) < 100
    assert smooth.shape == nearest.shape


def test_smooth_enlargement_matches_a_bicubic_resize():
    source = ideal_image((128, 128))
    tile = geometry.plan_grid((512, 512), get_profile("custom", tile=512, min_pixels=1))[0]
    smooth = np.asarray(cv.render_input(source, cv.Canvas((512, 512)), tile, (255, 0, 0), 6, "smooth")).astype(int)
    reference = np.asarray(source.resize((512, 512), Image.BICUBIC)).astype(int)
    assert np.abs(smooth - reference).mean() < 1.0


def test_init_option_flows_to_the_instructions(tmp_path):
    work, generator, ideal = make_job(tmp_path, size=(256, 256), factor=4,
                                      extra=("--profile", "custom", "--tile", "512", "--min-pixels", "1",
                                             "--enlarge", "smooth"))
    assert st.load(work)["options"]["enlarge"] == "smooth"
    status, out, err = run("next", "--work", work)
    assert "smoothly interpolated and therefore blurry" in out and "blocky nearest-neighbour" not in out


def test_default_is_nearest_and_the_stair_step_line_is_always_given(tmp_path):
    work, generator, ideal = make_job(tmp_path)
    assert st.load(work)["options"]["enlarge"] == "nearest"
    status, out, err = run("next", "--work", work)
    assert "blocky nearest-neighbour pixels" in out
    assert "stair-stepped" in out and "pixel look is part of the style" in out
