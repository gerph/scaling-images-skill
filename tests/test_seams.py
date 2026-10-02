import numpy as np
from PIL import Image

from scaling_images import canvas as cv
from scaling_images import geometry, seams
from scaling_images.profiles import get_profile
from synth import FakeGenerator, ideal_image

TARGET = (2560, 1920)


def setup():
    profile = get_profile("gpt-image-2-api")
    tiles = geometry.plan_grid(TARGET, profile)
    ideal = ideal_image(TARGET)
    source = ideal.resize((640, 480), Image.BOX)
    canvas = cv.Canvas(TARGET)
    generator = FakeGenerator(ideal)
    cv.merge(canvas, tiles[0], np.asarray(generator.generate(tiles[0])))
    tile = tiles[1]
    supplied = np.asarray(cv.render_input(source, canvas, tile, (255, 0, 0), 6))
    mask = canvas.window_mask(tile)
    return tile, canvas, generator, supplied, mask


def test_shift_is_estimated_and_corrected():
    tile, canvas, generator, supplied, mask = setup()
    returned = np.asarray(generator.generate(tile, shift=(3, -2)))
    dx, dy, peak = seams.estimate_offset(supplied, returned, mask)
    assert (dx, dy) == (3, -2)
    fixed = seams.align(returned, dx, dy)
    ideal = np.asarray(generator.generate(tile))
    assert np.abs(fixed[:, 100:700].astype(int) - ideal[:, 100:700].astype(int)).mean() < 0.5


def test_unshifted_tile_is_left_alone():
    tile, canvas, generator, supplied, mask = setup()
    returned = np.asarray(generator.generate(tile))
    assert seams.estimate_offset(supplied, returned, mask)[:2] == (0, 0)
    assert seams.align(returned, 0, 0) is returned


def test_tone_shift_is_matched_and_seam_improves():
    tile, canvas, generator, supplied, mask = setup()
    returned = np.asarray(generator.generate(tile, tone=(1.0, 25)))
    fixed = seams.tone_match(returned, supplied, mask)

    def ratio(window):
        trial = cv.Canvas(TARGET)
        trial.pixels[:] = canvas.pixels
        cv.merge(trial, tile, window)
        return seams.seam_report(trial.pixels, tile)["left"]["ratio"]

    assert ratio(returned) > 3.0
    assert ratio(fixed) < 1.5
    ideal = np.asarray(generator.generate(tile))
    assert np.abs(fixed.astype(int) - ideal.astype(int)).mean() < 1.5


def test_ideal_tile_unchanged_by_tone_match():
    tile, canvas, generator, supplied, mask = setup()
    ideal = np.asarray(generator.generate(tile))
    fixed = seams.tone_match(ideal, supplied, mask)
    assert np.abs(fixed.astype(int) - ideal.astype(int)).max() <= 1


def test_correlation_detects_scrambled_context():
    tile, canvas, generator, supplied, mask = setup()
    good = np.asarray(generator.generate(tile))
    bad = np.asarray(generator.generate(tile, scramble_context=True))
    assert seams.context_correlation(supplied, good, mask) > 0.95
    assert seams.context_correlation(supplied, bad, mask) < 0.5


def test_marker_remains_detected():
    tile, canvas, generator, supplied, mask = setup()
    clean = np.asarray(generator.generate(tile))
    dirty = np.asarray(generator.generate(tile, marker=((255, 0, 0), 6)))
    assert not seams.marker_remains(clean, tile, (255, 0, 0), 6)
    assert seams.marker_remains(dirty, tile, (255, 0, 0), 6)


def test_vertical_colour_gradient_is_corrected_where_global_tone_cannot():
    tile, canvas, generator, supplied, mask = setup()
    returned = np.asarray(generator.generate(tile, vgradient=(30, -30)))
    ideal = np.asarray(generator.generate(tile))

    def step(window):
        trial = cv.Canvas(TARGET)
        trial.pixels[:] = canvas.pixels
        cv.merge(trial, tile, window)
        return seams.seam_report(trial.pixels, tile)["left"]["ratio"]

    assert step(returned) > 2.5
    assert step(seams.tone_match(returned, supplied, mask)) > 2.5
    fixed = seams.tone_field(returned, supplied, tile)
    assert step(fixed) < 1.0
    assert np.abs(fixed[:, 800:].astype(int) - ideal[:, 800:].astype(int)).mean() < 4


def test_ideal_tile_is_unchanged_by_tone_field():
    tile, canvas, generator, supplied, mask = setup()
    ideal = np.asarray(generator.generate(tile))
    assert np.abs(seams.tone_field(ideal, supplied, tile).astype(int) - ideal.astype(int)).max() <= 1
