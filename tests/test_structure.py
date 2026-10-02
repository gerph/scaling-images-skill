import numpy as np

from scaling_images import canvas as cv
from scaling_images import geometry, seams
from scaling_images import state as st
from scaling_images.profiles import get_profile
from PIL import Image
from helpers import make_job, run, save_result
from synth import FakeGenerator, ideal_image

TARGET = (2560, 1920)


def setup():
    tiles = geometry.plan_grid(TARGET, get_profile("gpt-image-2-api"))
    ideal = ideal_image(TARGET)
    source = ideal.resize((640, 480), Image.BOX)
    canvas = cv.Canvas(TARGET)
    generator = FakeGenerator(ideal)
    tile = tiles[0]
    supplied = np.asarray(cv.render_input(source, canvas, tile, (255, 0, 0), 6))
    return tile, supplied, generator


def test_faithful_tile_scores_high_and_moved_content_scores_low():
    tile, supplied, generator = setup()
    good, _ = seams.structure_score(supplied, np.asarray(generator.generate(tile)), tile)
    assert good > 0.7
    # Content moved by 60 pixels (as when an edge has been redrawn in the wrong place).
    moved, worst = seams.structure_score(supplied, np.asarray(generator.generate(tile, shift=(0, 60))), tile)
    assert moved < good - 0.3 and worst


def test_restyled_colours_do_not_matter():
    tile, supplied, generator = setup()
    base, _ = seams.structure_score(supplied, np.asarray(generator.generate(tile)), tile)
    graded, _ = seams.structure_score(supplied, np.asarray(generator.generate(tile, tone=(0.6, 50))), tile)
    assert abs(base - graded) < 0.1


def test_accept_warns_about_drift_and_option_turns_it_off(tmp_path):
    work, generator, ideal = make_job(tmp_path)
    tile = st.next_pending(st.load(work))
    save_result(work, tile, generator.generate(tile, shift=(0, 60)))
    status, out, err = run("accept", "--work", work)
    assert status == 5 and "layout has drifted" in out

    other = tmp_path / "other"
    other.mkdir()
    work2, generator2, _ = make_job(other, extra=("--no-structure",))
    assert st.load(work2)["options"]["structure"] is False
    tile = st.next_pending(st.load(work2))
    save_result(work2, tile, generator2.generate(tile, shift=(0, 60)))
    status, out, err = run("accept", "--work", work2)
    assert "layout has drifted" not in out
