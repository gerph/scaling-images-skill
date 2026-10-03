import os

import numpy as np
from PIL import Image

from scaling_images import canvas as cv
from scaling_images import seams
from scaling_images import state as st
from helpers import DESCRIPTION, make_job, run, save_result
from synth import ideal_image

GRID = ("--profile", "custom", "--tile", "512", "--min-pixels", "1")


def lum(a):
    return a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114


def run_all(tmp_path, name, *extra, **defects):
    """
    A 3x3 job whose generator lightens every tile, accepted to the end; returns (work, canvas pixels).
    """
    folder = tmp_path / name
    folder.mkdir()
    work, generator, ideal = make_job(folder, size=(256, 256), factor=4, extra=GRID + extra)
    for _ in range(len(st.load(work)["tiles"])):
        tile = st.next_pending(st.load(work))
        save_result(work, tile, generator.generate(tile, tone=(1.25, 18)))
        assert run("accept", "--work", work)[0] in (0, 5)
    return work, cv.Canvas.load(work).pixels.copy()


def test_strength_scales_the_pull_to_the_original():
    ideal = np.asarray(ideal_image((512, 512)))
    lighter = np.clip(ideal.astype(float) * 1.5 + 20, 0, 255).astype(np.uint8)
    none = seams.anchor_to_original(lighter, ideal, 64, strength=0.0)
    half = seams.anchor_to_original(lighter, ideal, 64, strength=0.5)
    full = seams.anchor_to_original(lighter, ideal, 64, strength=1.0)
    assert np.array_equal(none, lighter)
    error = lambda a: abs(lum(a.astype(float)).mean() - lum(ideal.astype(float)).mean())
    assert error(full) < error(half) < error(none)
    assert error(half) > 0.3 * error(none) and error(half) < 0.7 * error(none)


def test_init_records_the_default_strength_and_rejects_nonsense(tmp_path):
    folder = tmp_path / "a"
    folder.mkdir()
    work, generator, ideal = make_job(folder, size=(256, 256), factor=4, extra=GRID)
    assert st.load(work)["options"]["anchor_strength"] == 0.5
    status, out, err = run("init", str(folder / "source.jpg"), "--factor", 4, "--anchor-strength", 2,
                           "--work", str(tmp_path / "b"), "--description", os.path.join(work, "description.md"), *GRID)
    assert status == 1 and "between 0 and 1" in err


def test_options_shows_and_changes_and_validates(tmp_path):
    folder = tmp_path / "a"
    folder.mkdir()
    work, generator, ideal = make_job(folder, size=(256, 256), factor=4, extra=GRID)
    status, out, err = run("options", "--work", work)
    assert status == 0 and "anchor_strength=0.5" in out
    status, out, err = run("options", "--anchor-strength", 0.2, "--feather", 64, "--tone", "off", "--work", work)
    assert status == 0 and "reprocess" in out
    options = st.load(work)["options"]
    assert options["anchor_strength"] == 0.2 and options["feather"] == 64 and options["tone"] is False
    assert run("options", "--anchor-strength", 3, "--work", work)[0] == 1
    assert st.load(work)["options"]["anchor_strength"] == 0.2


def test_reprocess_with_new_options_equals_a_fresh_run_with_them(tmp_path):
    work_a, canvas_a = run_all(tmp_path, "a", "--anchor-strength", "1.0")
    work_b, canvas_b = run_all(tmp_path, "b", "--anchor-strength", "0.25")
    assert not np.array_equal(canvas_a, canvas_b)

    assert run("options", "--anchor-strength", 0.25, "--work", work_a)[0] == 0
    status, out, err = run("reprocess", "--yes", "--work", work_a)
    assert status == 0, err + out
    assert "Lightness against the original" in out
    assert np.array_equal(cv.Canvas.load(work_a).pixels, canvas_b)
    assert os.path.isfile(os.path.join(work_a, "reprocess-backup", "canvas.png"))
    assert np.array_equal(np.asarray(Image.open(os.path.join(work_a, "reprocess-backup", "canvas.png"))), canvas_a)


def test_reprocess_needs_confirmation_and_changes_nothing_without_it(tmp_path):
    work, canvas = run_all(tmp_path, "a")
    before = open(os.path.join(work, "state.json"), "rb").read()
    status, out, err = run("reprocess", "--work", work)
    assert status == 4 and "re-run with --yes" in err
    assert open(os.path.join(work, "state.json"), "rb").read() == before
    assert np.array_equal(cv.Canvas.load(work).pixels, canvas)


def test_reprocess_keeps_statuses_and_a_later_start_leaves_earlier_tiles_alone(tmp_path):
    work, canvas = run_all(tmp_path, "a")
    statuses = [t["status"] for t in st.load(work)["tiles"]]
    assert run("options", "--anchor-strength", 0, "--work", work)[0] == 0
    assert run("reprocess", "--from", "r1c0", "--yes", "--work", work)[0] == 0
    state = st.load(work)
    assert [t["status"] for t in state["tiles"]] == statuses
    after = cv.Canvas.load(work).pixels
    first_row = state["tiles"][3]["acc"][1]
    assert np.array_equal(after[:first_row - 130], canvas[:first_row - 130])    # above r1's feather band
    assert not np.array_equal(after, canvas)


def test_reprocess_with_a_missing_result_changes_nothing(tmp_path):
    work, canvas = run_all(tmp_path, "a")
    state = st.load(work)
    os.remove(os.path.join(st.tile_dir(work, state["tiles"][4]), "result.png"))
    before = open(os.path.join(work, "state.json"), "rb").read()
    status, out, err = run("reprocess", "--yes", "--work", work)
    assert status == 1 and "no stored result for r1c1" in err
    assert open(os.path.join(work, "state.json"), "rb").read() == before
    assert np.array_equal(cv.Canvas.load(work).pixels, canvas)


def test_a_run_continues_normally_after_reprocessing(tmp_path):
    folder = tmp_path / "a"
    folder.mkdir()
    work, generator, ideal = make_job(folder, size=(256, 256), factor=4, extra=GRID)
    for _ in range(4):
        tile = st.next_pending(st.load(work))
        save_result(work, tile, generator.generate(tile, tone=(1.25, 18)))
        run("accept", "--work", work)
    assert run("reprocess", "--yes", "--work", work)[0] == 0
    assert st.next_pending(st.load(work))["index"] == 4
    for _ in range(5):
        tile = st.next_pending(st.load(work))
        save_result(work, tile, generator.generate(tile, tone=(1.25, 18)))
        assert run("accept", "--work", work)[0] in (0, 5)
    assert run("finish", "--work", work)[0] == 0
