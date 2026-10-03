import os

from scaling_images import state as st
from helpers import make_job, run, save_result


def snapshot(work):
    out = {}
    for name in ("state.json", "canvas.png", "mask.png"):
        with open(os.path.join(work, name), "rb") as handle:
            out[name] = handle.read()
    return out


def test_check_reports_without_changing_anything(tmp_path):
    work, generator, ideal = make_job(tmp_path)
    tile = st.next_pending(st.load(work))
    save_result(work, tile, generator.generate(tile))
    before = snapshot(work)
    status, out, err = run("check", "--work", work)
    assert status == 0 and "would be accepted" in out and "were not changed" in out
    assert snapshot(work) == before
    assert st.next_pending(st.load(work))["index"] == 0
    # The real accept afterwards still works.
    assert run("accept", "--work", work)[0] == 0


def test_check_gives_the_same_verdicts_as_accept(tmp_path):
    work, generator, ideal = make_job(tmp_path)
    tile = st.next_pending(st.load(work))
    save_result(work, tile, generator.generate(tile))
    assert run("accept", "--work", work)[0] == 0
    tile = st.next_pending(st.load(work))
    before = snapshot(work)

    save_result(work, tile, generator.generate(tile, resize=(1000, 1000)))
    assert run("check", "--work", work)[0] == 2

    colour = tuple(st.load(work)["marker"]["colour"])
    save_result(work, tile, generator.generate(tile, marker=(colour, 6)))
    status, out, err = run("check", "--work", work)
    assert status == 2 and "marker" in err

    save_result(work, tile, generator.generate(tile, shift=(3, -2)))
    status, out, err = run("check", "--work", work)
    assert status == 5 and "displaced" in out

    assert snapshot(work) == before


def test_check_warns_about_layout_drift_on_the_first_tile(tmp_path):
    work, generator, ideal = make_job(tmp_path)
    tile = st.next_pending(st.load(work))
    save_result(work, tile, generator.generate(tile, shift=(0, 60)))
    before = snapshot(work)
    status, out, err = run("check", "--work", work)
    assert status == 5 and "layout has drifted" in out
    assert snapshot(work) == before


def test_check_accepts_an_explicit_candidate_path(tmp_path):
    work, generator, ideal = make_job(tmp_path)
    tile = st.next_pending(st.load(work))
    candidate = str(tmp_path / "attempt.png")
    generator.generate(tile).save(candidate)
    status, out, err = run("check", candidate, "--work", work)
    assert status == 0, err


def test_instructions_say_what_not_to_draw(tmp_path):
    work, generator, ideal = make_job(tmp_path)
    status, out, err = run("next", "--work", work)
    assert "Keep the exact framing" in out and "lies outside this tile" in out
    assert "do not turn it into smooth colour" in out


def test_check_writes_candidate_seam_crops_that_accept_then_matches(tmp_path):
    import numpy as np
    from PIL import Image
    work, generator, ideal = make_job(tmp_path)
    tile = st.next_pending(st.load(work))
    save_result(work, tile, generator.generate(tile))
    assert run("accept", "--work", work)[0] == 0
    tile = st.next_pending(st.load(work))
    save_result(work, tile, generator.generate(tile, noise=8))
    before = snapshot(work)
    status, out, err = run("check", "--work", work)
    directory = st.tile_dir(work, tile)
    candidate = os.path.join(directory, "candidate-seam-left.png")
    assert os.path.isfile(candidate) and "Look at the proposed seam" in out
    assert not os.path.exists(os.path.join(directory, "seam-left.png"))
    assert snapshot(work) == before

    # The crop is what accept then produces, so the check shows the real result.
    run("accept", "--work", work)
    assert np.array_equal(np.asarray(Image.open(candidate)),
                          np.asarray(Image.open(os.path.join(directory, "seam-left.png"))))
