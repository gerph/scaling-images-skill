# Scaling images skill

An agent skill that enlarges an image beyond what an image generator can draw in one go, keeping
the style consistent and the joins invisible. The skill is in `skills/scaling-images/`; the design
is in `design/`.

Install the dependencies with `python3 skills/scaling-images/scripts/scale_image.py setup`
(or `setup --venv DIR`). Run the tests with `pip install -r requirements-dev.txt` and `pytest tests/`
(they use a fake generator and need no network or tokens; the suite takes a few minutes).

Licence: MIT.
