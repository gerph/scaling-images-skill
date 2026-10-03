# Distributing the skill

The skill is the single directory `skills/scaling-images/`. It is self-contained: `SKILL.md`, `references/`, `scripts/`
(the Python code and `requirements.txt`) and `agents/openai.yaml`. Nothing else in this repository is shipped.

## Adding it to an agent-skills repository

Written for a repository laid out like `gerph/riscos-agent-skills`, where each skill is a directory under `skills/` and
the plugin manifests point at that folder, so a new skill needs no registration.

1. Copy `skills/scaling-images/` to `skills/scaling-images/` in the target repository (leave out `__pycache__`).
2. Add a line to the target's README skill list, for example under a new "Images" heading:

       * `scaling-images`: Enlarging images beyond a generator's size limit, tile by tile, with consistent style and seamless joins.

3. Run the target's `python3 check-skills.py`; it is the same checker as in this repository.
4. Raise the target's version with its `update-version` script (a new skill is a minor version), and commit.
5. If the target's plugin descriptions are specific to one topic, decide whether to widen them: the skill itself is
   not specific to RISC OS.

## A release of this repository

1. Update `CHANGELOG.md` (change `unreleased` to a date) and the version in
   `skills/scaling-images/scripts/scaling_images/__init__.py`. The test `test_changelog_names_the_current_version`
   keeps them in step, and CI refuses a tag that does not match the version the scripts report.
2. Run `python3 check-skills.py` and `pytest tests/`.
3. Tag `vX.Y.Z`. CI then builds `scaling-images.skill` (a zip of the skill directory) and drafts a release with it attached.

## Before each release

- Run a real job (a small image, a generator you have) to confirm the instructions still work with it; the tests use a
  fake generator and cannot tell.
- Check `references/generator-profiles.md` against current generator limits: the figures there come from public sources
  and go out of date.
