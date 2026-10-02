import io
import contextlib
import os

from PIL import Image

from scaling_images import commands
from scaling_images import state as st
from synth import FakeGenerator, ideal_image

DESCRIPTION = """# Style
Photograph with soft focus.

```json
{"content": [
  {"name": "left kitten", "note": "ginger", "box": [0.1, 0.4, 0.4, 0.8]},
  {"name": "hills", "note": "distant", "box": [0.0, 0.2, 1.0, 0.4]}
]}
```
"""


def run(*argv):
    """
    Run a command in-process; returns (status, stdout, stderr).
    """
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        status = commands.main([str(a) for a in argv])
    return status, out.getvalue(), err.getvalue()


def make_job(tmp_path, size=(640, 480), factor=4, extra=()):
    """
    A source JPEG and description in tmp_path, plus the ideal image; runs init.
    """
    target = (int(size[0] * factor), int(size[1] * factor))
    ideal = ideal_image(target)
    source_path = str(tmp_path / "source.jpg")
    ideal.resize(size, Image.BOX).save(source_path, quality=95)
    work = str(tmp_path / "work")
    os.makedirs(work)
    with open(os.path.join(work, "description.md"), "w") as handle:
        handle.write(DESCRIPTION)
    status, out, err = run("init", source_path, "--factor", factor, "--work", work, *extra)
    assert status == 0, err
    return work, FakeGenerator(ideal), ideal


def save_result(work, tile, image):
    directory = st.tile_dir(work, tile)
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, "result.png")
    image.save(path)
    return path
