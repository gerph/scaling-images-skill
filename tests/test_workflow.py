import os

import numpy as np
import pytest
from PIL import Image

from scaling_images import state as st
from helpers import DESCRIPTION, make_job, run, save_result


def current_tile(work):
    return st.next_pending(st.load(work))


def test_init_plans_two_tiles_for_kittens_sized_job(tmp_path):
    work, generator, ideal = make_job(tmp_path)
    state = st.load(work)
    assert state["target"] == [2560, 1920]
    assert [t["acc"] for t in state["tiles"]] == [[0, 0, 1280, 1920], [1280, 0, 2560, 1920]]
    assert state["marker"]["name"] in ("red", "magenta", "green", "cyan", "yellow")


def test_init_refuses_changed_aspect_ratio(tmp_path):
    work, generator, ideal = make_job(tmp_path)
    status, out, err = run("init", str(tmp_path / "source.jpg"), "--target", "2560x1440",
                           "--work", str(tmp_path / "w2"), "--description", os.path.join(work, "description.md"))
    assert status == 1 and "aspect ratio" in err


def test_init_needs_a_description(tmp_path):
    work, generator, ideal = make_job(tmp_path)
    status, out, err = run("init", str(tmp_path / "source.jpg"), "--factor", 4, "--work", str(tmp_path / "w3"))
    assert status == 1 and "description" in err.lower()


def test_state_survives_reread(tmp_path):
    work, generator, ideal = make_job(tmp_path)
    assert st.load(work) == st.load(work)


def test_next_instructions(tmp_path):
    work, generator, ideal = make_job(tmp_path)
    status, out, err = run("next", "--work", work)
    assert status == 0
    assert "Redraw all of it" in out and "marker" not in out.lower().split("redraw all of it")[0]
    assert "left kitten" in out and "To be drawn" in out
    assert "Photograph with soft focus" in out
    # Stable across a re-run.
    assert run("next", "--work", work)[1] == out

    state = st.load(work)
    save_result(work, state["tiles"][0], generator.generate(state["tiles"][0]))
    assert run("accept", "--work", work)[0] == 0
    status, out, err = run("next", "--work", work)
    assert "vertical line" in out and "LEFT" in out
    assert "continue it, do not repeat it" in out or "hills" in out
    assert "Already drawn in the finished artwork" in out


def test_full_run_with_ideal_generator_reproduces_ideal(tmp_path):
    work, generator, ideal = make_job(tmp_path)
    for _ in range(2):
        assert run("next", "--work", work)[0] == 0
        tile = current_tile(work)
        save_result(work, tile, generator.generate(tile))
        assert run("accept", "--work", work)[0] == 0
    assert run("next", "--work", work)[0] == 0
    status, out, err = run("finish", "--work", work)
    assert status == 0, err
    final = Image.open(os.path.join(work, "source-2560x1920.png"))
    assert final.size == (2560, 1920)
    assert np.array_equal(np.asarray(final), np.asarray(ideal))
    assert os.path.isfile(os.path.join(work, "preview.png"))


def test_finish_before_complete_is_refused(tmp_path):
    work, generator, ideal = make_job(tmp_path)
    status, out, err = run("finish", "--work", work)
    assert status == 1 and "r0c0" in err


def accept_first(work, generator, **defects):
    run("next", "--work", work)
    tile = current_tile(work)
    save_result(work, tile, generator.generate(tile))
    assert run("accept", "--work", work)[0] == 0


def test_accept_wrong_size_same_shape_is_resized_and_warned(tmp_path):
    work, generator, ideal = make_job(tmp_path)
    tile = current_tile(work)
    save_result(work, tile, generator.generate(tile, resize=(1024, 960)))
    status, out, err = run("accept", "--work", work)
    assert status == 5 and "resized" in out and "softer" in out


def test_accept_wrong_shape_is_rejected(tmp_path):
    work, generator, ideal = make_job(tmp_path)
    tile = current_tile(work)
    save_result(work, tile, generator.generate(tile, resize=(1000, 1000)))
    status, out, err = run("accept", "--work", work)
    assert status == 2 and "shape" in err
    assert current_tile(work)["index"] == 0


def test_accept_marker_left_behind_is_rejected(tmp_path):
    work, generator, ideal = make_job(tmp_path)
    accept_first(work, generator)
    state = st.load(work)
    colour = tuple(state["marker"]["colour"])
    tile = state["tiles"][1]
    save_result(work, tile, generator.generate(tile, marker=(colour, 6)))
    status, out, err = run("accept", "--work", work)
    assert status == 2 and "marker" in err


def test_accept_shifted_tile_is_corrected(tmp_path):
    work, generator, ideal = make_job(tmp_path)
    accept_first(work, generator)
    tile = st.load(work)["tiles"][1]
    save_result(work, tile, generator.generate(tile, shift=(3, -2)))
    status, out, err = run("accept", "--work", work)
    assert status == 5 and "displaced by (3, -2)" in out


def test_accept_scrambled_context_is_rejected(tmp_path):
    work, generator, ideal = make_job(tmp_path)
    accept_first(work, generator)
    tile = st.load(work)["tiles"][1]
    save_result(work, tile, generator.generate(tile, scramble_context=True))
    status, out, err = run("accept", "--work", work)
    assert status == 2 and "context" in err


def test_accept_tone_shift_is_matched(tmp_path):
    work, generator, ideal = make_job(tmp_path)
    accept_first(work, generator)
    tile = st.load(work)["tiles"][1]
    save_result(work, tile, generator.generate(tile, tone=(1.0, 25)))
    status, out, err = run("accept", "--work", work)
    assert status == 0, out


def test_description_change_pauses_and_changes_nothing(tmp_path):
    work, generator, ideal = make_job(tmp_path)
    accept_first(work, generator)
    before = open(os.path.join(work, "state.json")).read()
    path = os.path.join(work, "description.md")

    # A whitespace-only edit does not pause.
    open(path, "w").write(DESCRIPTION.replace("\n", "  \n"))
    assert run("next", "--work", work)[0] == 0

    open(path, "w").write(DESCRIPTION.replace("soft", "crisp"))
    before = open(os.path.join(work, "state.json")).read()
    tile = current_tile(work)
    save_result(work, tile, generator.generate(tile))
    status, out, err = run("accept", "--work", work)
    assert status == 3 and "Stop and ask the user" in err
    assert open(os.path.join(work, "state.json")).read() == before
    assert run("next", "--work", work)[0] == 3
    assert run("status", "--work", work)[0] == 0
    assert run("preview", "--work", work)[0] == 0

    status, out, err = run("description", "--adopt", "--work", work)
    assert status == 0
    state = st.load(work)
    assert len(state["description"]["history"]) == 2
    assert state["description"]["history"][-1]["from_tile"] == 1
    assert run("accept", "--work", work)[0] == 0


def test_description_change_redo_from_a_tile(tmp_path):
    work, generator, ideal = make_job(tmp_path)
    accept_first(work, generator)
    open(os.path.join(work, "description.md"), "w").write(DESCRIPTION.replace("soft", "crisp"))
    status, out, err = run("description", "--adopt", "--redo-from", "r0c0", "--work", work)
    assert status == 4
    status, out, err = run("description", "--adopt", "--redo-from", "r0c0", "--yes", "--work", work)
    assert status == 0
    assert current_tile(work)["index"] == 0
