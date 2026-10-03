import os

import numpy as np
from PIL import Image

from scaling_images import state as st
from helpers import make_job, run, save_result

GRID = ("--profile", "custom", "--tile", "512", "--min-pixels", "1")


def make_grid(tmp_path):
    return make_job(tmp_path, size=(256, 256), factor=4, extra=GRID)


def do_next_tile(work, generator):
    assert run("next", "--work", work)[0] == 0
    tile = st.next_pending(st.load(work))
    save_result(work, tile, generator.generate(tile))
    assert run("accept", "--work", work)[0] == 0


def test_three_by_three_grid_reproduces_ideal(tmp_path):
    work, generator, ideal = make_grid(tmp_path)
    state = st.load(work)
    assert len(state["tiles"]) == 9
    for _ in range(9):
        do_next_tile(work, generator)
    assert run("next", "--work", work)[0] == 0
    assert run("finish", "--work", work, "--output", str(tmp_path / "out.png"))[0] == 0
    final = Image.open(str(tmp_path / "out.png"))
    assert np.abs(np.asarray(final).astype(int) - np.asarray(ideal).astype(int)).max() <= 8


def test_interrupted_run_resumes_from_state(tmp_path):
    work, generator, ideal = make_grid(tmp_path)
    for _ in range(4):
        do_next_tile(work, generator)
    # A later session has only the work directory.
    status, out, err = run("status", "--work", work)
    assert status == 0 and "[kept]" in out or "[accepted]" in out
    assert st.next_pending(st.load(work))["index"] == 4
    for _ in range(5):
        do_next_tile(work, generator)
    assert run("finish", "--work", work)[0] == 0


def test_redo_lists_dependents_and_needs_confirmation(tmp_path):
    work, generator, ideal = make_grid(tmp_path)
    for _ in range(9):
        do_next_tile(work, generator)

    status, out, err = run("redo", "r0c0", "--work", work)
    assert status == 4 and "discards 9 tile(s)" in out
    assert all(t["status"] != "pending" for t in st.load(work)["tiles"])

    status, out, err = run("redo", "r2c1", "--work", work)
    assert status == 4 and "r2c1, r2c2" in out
    assert run("redo", "r2c1", "--yes", "--work", work)[0] == 0
    state = st.load(work)
    assert [t["status"] for t in state["tiles"]].count("pending") == 2
    assert st.next_pending(state)["index"] == 7

    # Redoing the last accepted tile costs nothing extra.
    do_next_tile(work, generator)
    do_next_tile(work, generator)
    status, out, err = run("redo", "r2c2", "--work", work)
    assert "discards 1 tile(s)" in out


def test_redo_of_unaccepted_tile_is_an_error(tmp_path):
    work, generator, ideal = make_grid(tmp_path)
    status, out, err = run("redo", "r0c0", "--yes", "--work", work)
    assert status == 1 and "nothing to redo" in err


def test_redo_then_accept_replaces_pixels(tmp_path):
    work, generator, ideal = make_grid(tmp_path)
    for _ in range(9):
        do_next_tile(work, generator)
    assert run("redo", "r2c2", "--yes", "--work", work)[0] == 0
    do_next_tile(work, generator)
    assert run("finish", "--work", work, "--output", str(tmp_path / "out.png"))[0] == 0


def test_preview_reports_seams(tmp_path):
    work, generator, ideal = make_grid(tmp_path)
    for _ in range(2):
        do_next_tile(work, generator)
    status, out, err = run("preview", "--work", work)
    assert status == 0 and "left seam" in out
    assert os.path.isfile(os.path.join(work, "preview.png"))


def test_probe_recommends_a_tile_that_fits(tmp_path):
    work, generator, ideal = make_grid(tmp_path)
    status, out, err = run("probe", "--work", work)
    assert status == 0 and "512x512" in out
    # The generator delivers more than asked for.
    Image.new("RGB", (640, 640)).save(os.path.join(work, "probe", "result.png"))
    status, out, err = run("probe", "--result", os.path.join(work, "probe", "result.png"), "--work", work)
    assert "MORE than was asked" in out and "--tile 640" in out
    # The generator delivers a different, smaller shape.
    Image.new("RGB", (400, 300)).save(os.path.join(work, "probe", "result.png"))
    status, out, err = run("probe", "--result", os.path.join(work, "probe", "result.png"), "--work", work)
    assert status == 0 and "not honoured" in out and "--tile 288" in out

    Image.new("RGB", (512, 512)).save(os.path.join(work, "probe", "result.png"))
    status, out, err = run("probe", "--result", os.path.join(work, "probe", "result.png"), "--work", work)
    assert "honoured: keep --tile 512" in out
