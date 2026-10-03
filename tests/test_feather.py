import numpy as np
from PIL import Image

from scaling_images import canvas as cv
from scaling_images import geometry, seams
from scaling_images import state as st
from scaling_images.profiles import get_profile
from helpers import make_job, run, save_result
from synth import FakeGenerator, ideal_image

TARGET = (2560, 1920)


def setup():
    tiles = geometry.plan_grid(TARGET, get_profile("gpt-image-2-api"))
    ideal = ideal_image(TARGET)
    canvas = cv.Canvas(TARGET)
    generator = FakeGenerator(ideal)
    cv.merge(canvas, tiles[0], np.asarray(generator.generate(tiles[0])))
    return tiles[1], canvas, generator, ideal


def test_feather_of_an_identical_copy_changes_nothing():
    tile, canvas, generator, ideal = setup()
    before = canvas.pixels.copy()
    cv.apply_feather(canvas, tile, np.asarray(generator.generate(tile)), 128)
    assert np.array_equal(canvas.pixels, before)


def test_feather_is_a_ramp_ending_at_the_returned_copy():
    tile, canvas, generator, ideal = setup()
    original = canvas.pixels.copy()
    returned = np.asarray(generator.generate(tile, tone=(1.0, 40)))
    cv.merge(canvas, tile, returned)
    backups = cv.apply_feather(canvas, tile, returned, 128)

    ax0 = tile["acc"][0]
    (rect, saved), = backups.values()
    assert rect == (ax0 - 128, 0, ax0, 1920)
    assert np.array_equal(saved, original[:, ax0 - 128:ax0])
    # Start of the band is almost the canvas; the end is almost the generator's copy.
    first = np.abs(canvas.pixels[:, ax0 - 128].astype(int) - original[:, ax0 - 128].astype(int)).mean()
    last = np.abs(canvas.pixels[:, ax0 - 1].astype(int) - returned[:, ax0 - 1 - tile["win"][0]].astype(int)).mean()
    assert first < 1.0 and last < 1.0
    # Pixels outside the band are untouched.
    assert np.array_equal(canvas.pixels[:, :ax0 - 128], original[:, :ax0 - 128])


def test_feather_makes_a_colour_step_gradual():
    tile, canvas, generator, ideal = setup()
    returned = np.asarray(generator.generate(tile, tone=(1.0, 30)))
    hard = cv.Canvas(TARGET)
    hard.pixels[:] = canvas.pixels
    cv.merge(hard, tile, returned)
    soft = cv.Canvas(TARGET)
    soft.pixels[:] = hard.pixels
    soft.pixels[:, :1280] = canvas.pixels[:, :1280]
    cv.apply_feather(soft, tile, returned, 128)

    def biggest_column_jump(pixels):
        row = pixels[:, 1100:1400].astype(float).mean(axis=(0, 2))
        return np.abs(np.diff(row)).max()

    assert biggest_column_jump(soft.pixels) < biggest_column_jump(hard.pixels) / 5


def test_accept_feathers_and_redo_restores_the_canvas(tmp_path):
    work, generator, ideal = make_job(tmp_path)
    run("next", "--work", work)
    tile = st.next_pending(st.load(work))
    save_result(work, tile, generator.generate(tile))
    assert run("accept", "--work", work)[0] == 0
    before = cv.Canvas.load(work).pixels.copy()
    tile = st.next_pending(st.load(work))
    save_result(work, tile, generator.generate(tile, noise=12))
    status, out, err = run("accept", "--work", work)
    assert status in (0, 5)

    state = st.load(work)
    assert "left" in state["tiles"][1]["feather"]
    canvas = cv.Canvas.load(work)
    ax0 = state["tiles"][1]["acc"][0]
    assert not np.array_equal(canvas.pixels[:, ax0 - 128:ax0], before[:, ax0 - 128:ax0])

    assert run("redo", "r0c1", "--yes", "--work", work)[0] == 0
    canvas = cv.Canvas.load(work)
    assert np.array_equal(canvas.pixels[:, ax0 - 128:ax0], before[:, ax0 - 128:ax0])
    assert st.load(work)["tiles"][1]["feather"] == {}


def test_feather_can_be_turned_off(tmp_path):
    work, generator, ideal = make_job(tmp_path, extra=("--feather", "0"))
    assert st.load(work)["options"]["feather"] == 0
