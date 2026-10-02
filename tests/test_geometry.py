import pytest

from scaling_images import geometry
from scaling_images.geometry import AspectRatioError, GeometryError
from scaling_images.profiles import get_profile


def test_target_from_factor():
    assert geometry.target_size((640, 480), factor=4) == (2560, 1920)
    assert geometry.target_size((101, 51), factor=1.5) == (152, 77)


def test_target_from_resolution_and_aspect_error():
    assert geometry.target_size((640, 480), target=(2560, 1920)) == (2560, 1920)
    with pytest.raises(AspectRatioError):
        geometry.target_size((640, 480), target=(2560, 1440))


def test_target_needs_one_of_factor_or_target():
    with pytest.raises(GeometryError):
        geometry.target_size((640, 480))


def test_axis_2560_gives_two_equal_slices():
    assert geometry.plan_axis(2560, 2048, 683, 512) == [1280, 1280]


def test_axis_6144_full_first_slice():
    assert geometry.plan_axis(6144, 2048, 683, 512) == [2048, 1024, 1024, 1024, 1024]


def test_axis_that_fits_is_one_slice():
    assert geometry.plan_axis(1920, 2048, 683, 512) == [1920]


@pytest.mark.parametrize("tile", [1024, 2048, 3072])
def test_axis_never_a_sliver(tile):
    context = int(round(tile / 3.0))
    minimum = tile // 4
    cap = tile - context
    for length in range(1, 10001, 7):
        slices = geometry.plan_axis(length, tile, context, minimum)
        assert sum(slices) == length
        if length > tile:
            assert min(slices) >= minimum
            assert max(slices[1:]) <= cap
            assert slices[0] <= tile


def test_grid_for_kittens():
    profile = get_profile("gpt-image-2-api")
    tiles = geometry.plan_grid((2560, 1920), profile)
    assert len(tiles) == 2
    first, second = tiles
    assert first["acc"] == [0, 0, 1280, 1920]
    assert first["win"] == [0, 0, 2048, 1920]
    assert first["size"] == [2048, 1920]
    assert second["acc"] == [1280, 0, 2560, 1920]
    assert second["win"] == [512, 0, 2560, 1920]
    assert second["marker_left"] and not second["marker_top"]


def test_grid_windows_obey_profile():
    profile = get_profile("gpt-image-2-api")
    for tile in geometry.plan_grid((6144, 4100), profile):
        w, h = tile["size"]
        assert w % 16 == 0 and h % 16 == 0
        assert tile["win"][2] - tile["win"][0] + tile["pad"][0] == w


def test_grid_rounds_up_to_multiple_with_padding():
    profile = get_profile("custom", min_pixels=1)
    tiles = geometry.plan_grid((1000, 700), profile)
    assert len(tiles) == 1
    assert tiles[0]["size"] == [1008, 704]
    assert tiles[0]["pad"] == [8, 4]


def test_grid_rejects_window_outside_limits():
    profile = get_profile("gpt-image-2-api")
    with pytest.raises(GeometryError):
        geometry.plan_grid((640, 480), profile)


def test_dependents_are_transitive():
    profile = get_profile("gpt-image-2-api")
    tiles = geometry.plan_grid((4096, 4096), profile)
    assert geometry.dependents(tiles, 0)  # right and below neighbours
    assert geometry.dependents(tiles, len(tiles) - 1) == []
