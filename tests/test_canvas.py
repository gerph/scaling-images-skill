import numpy as np
from PIL import Image

from scaling_images import canvas as cv
from scaling_images import geometry
from scaling_images.profiles import get_profile
from synth import FakeGenerator, ideal_image

TARGET = (2560, 1920)


def make(profile_name="gpt-image-2-api"):
    profile = get_profile(profile_name)
    tiles = geometry.plan_grid(TARGET, profile)
    ideal = ideal_image(TARGET)
    source = ideal.resize((640, 480), Image.BOX)
    return tiles, ideal, source


def test_first_tile_is_nearest_upscale_without_markers():
    tiles, ideal, source = make()
    canvas = cv.Canvas(TARGET)
    image = cv.render_input(source, canvas, tiles[0], (255, 0, 0), 6)
    assert image.size == (2048, 1920)
    expected = np.asarray(source.resize((2560, 1920), Image.NEAREST))[:, :2048]
    assert np.array_equal(np.asarray(image), expected)


def test_second_tile_has_vertical_marker_at_first_unknown_column():
    tiles, ideal, source = make()
    canvas = cv.Canvas(TARGET)
    generator = FakeGenerator(ideal)
    cv.merge(canvas, tiles[0], np.asarray(generator.generate(tiles[0])))
    image = np.asarray(cv.render_input(source, canvas, tiles[1], (255, 0, 0), 6))
    ux = tiles[1]["acc"][0] - tiles[1]["win"][0]
    assert ux == 768
    assert (image[:, ux:ux + 6] == (255, 0, 0)).all()
    # Accepted pixels left of the marker are the canvas's, not nearest-neighbour.
    assert np.array_equal(image[:, :ux], canvas.pixels[:, 512:512 + ux])
    # The marker does not extend past its width.
    assert not (image[:, ux + 6] == (255, 0, 0)).all()


def test_both_markers_in_second_row():
    profile = get_profile("gpt-image-2-api")
    target = (4096, 4096)
    tiles = geometry.plan_grid(target, profile)
    last = tiles[-1]
    assert last["marker_left"] and last["marker_top"]
    canvas = cv.Canvas(target)
    canvas.mask[:] = False
    source = ideal_image((1024, 1024))
    image = np.asarray(cv.render_input(source, canvas, last, (255, 0, 0), 6))
    ux, uy = cv.unknown_origin(last)
    assert (image[uy:, ux:ux + 6] == (255, 0, 0)).all()
    assert (image[uy:uy + 6, ux:] == (255, 0, 0)).all()


def test_mostly_red_source_gets_a_non_red_marker():
    source = Image.new("RGB", (100, 100), (250, 10, 10))
    name, colour = cv.choose_marker_colour(source)
    assert name != "red"
    name, _ = cv.choose_marker_colour(Image.new("RGB", (100, 100), (20, 30, 200)))
    assert name == "red"


def test_merge_takes_only_the_new_region():
    tiles, ideal, source = make()
    canvas = cv.Canvas(TARGET)
    generator = FakeGenerator(ideal)
    cv.merge(canvas, tiles[0], np.asarray(generator.generate(tiles[0])))
    assert canvas.mask[:, :1280].all() and not canvas.mask[:, 1280:].any()
    cv.merge(canvas, tiles[1], np.asarray(generator.generate(tiles[1])))
    assert canvas.mask.all()
    assert np.array_equal(canvas.pixels, np.asarray(ideal))


def test_padded_window_is_cropped_on_merge():
    profile = get_profile("custom", min_pixels=1)
    tiles = geometry.plan_grid((1000, 700), profile)
    ideal = ideal_image((1000, 700))
    canvas = cv.Canvas((1000, 700))
    window = np.asarray(FakeGenerator(ideal).generate(tiles[0]))
    assert window.shape[:2] == (704, 1008)
    cv.merge(canvas, tiles[0], window)
    assert np.array_equal(canvas.pixels, np.asarray(ideal))


def test_save_and_load_round_trip(tmp_path):
    canvas = cv.Canvas((32, 16))
    canvas.pixels[2:4, 3:5] = (1, 2, 3)
    canvas.mask[2:4, 3:5] = True
    canvas.save(str(tmp_path))
    again = cv.Canvas.load(str(tmp_path))
    assert np.array_equal(again.pixels, canvas.pixels)
    assert np.array_equal(again.mask, canvas.mask)
