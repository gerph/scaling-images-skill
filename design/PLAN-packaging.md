# Plan: Packaging

Part of the [implementation plan](OVERVIEW.md#implementation-plan). Implements
[DESIGN-packaging.md](DESIGN-packaging.md).

## Dependencies

- Stage 1 is foundational: **do this first.**
- Stages 2 to 4 depend on [PLAN-workflow.md](PLAN-workflow.md) Stage 3 or
  later.
- Stage 5 depends on everything else.

## Stages

### Stage 1 — Skeleton, entry point and setup

- [ ] Layout: `skills/scaling-images/{scripts/scale_image.py,
      scripts/scaling_images/, references/}`, `tests/`, `requirements.txt`
      (Pillow and numpy, minimum versions), `LICENSE` (MIT), `README.md`.
- [ ] `scale_image.py`: subcommand dispatch; dependency check printing the
      exact install command; re-launch under a recorded venv.
- [ ] `setup` (`--venv <dir>`, `--check`); handles the "externally managed"
      refusal with a venv recommendation.
- [ ] Authorship header (Charles Ferguson, Gerph) in each script; Python 3.9
      or later.

**Acceptance:** `pytest tests/test_setup.py`: with Pillow hidden, the entry point
prints the install command and exits non-zero; `setup --venv <tmp>` creates a
working venv and a later run uses it; `setup --check` reports the versions.

**Notes:** The tests use a temporary directory and never change the user's
Python.

### Stage 2 — `SKILL.md` and references

- [ ] Read the repository's skill-writing guidance (`updating-robe-skills`)
      first.
- [ ] `SKILL.md`: when to use it, the workflow in order (describe, review with
      the user, init, probe, loop of next/generate/accept, preview, finish),
      what to ask the user, agent-neutral wording, pointers to the references.
- [ ] `references/`: description format (from the Description plan, Stage 4),
      generator profiles with the researched limits and sources, seam
      treatments and what to do when a seam is rejected.

**Acceptance:** the header is valid (name equals directory, description
present); every file referenced exists.

### Stage 3 — Package test

- [ ] `tests/test_package.py`: copies only the shipped files into a clean
      directory, checks the header and links, runs `setup --venv`, and runs a
      small fake-generator job from that copy.

**Acceptance:** `pytest tests/test_package.py` passes from a clean checkout.

### Stage 4 — Changelog and release notes

- [ ] `CHANGELOG.md` with the first version entry; version number in one place.

**Acceptance:** version printed by `scale_image.py --version` matches the
changelog.

### Stage 5 — Trial on real generators

- [ ] Run `KittensSmall.jpg` at 4x end to end with the Codex built-in tool
      (probe first) and, where possible, with explicit sizes.
- [ ] Record: delivered sizes, seam reports and crops, what failed.
- [ ] Decide which of the further seam treatments, the patch redo and
      progressive enlargement are needed; move each decision into the design
      or [IDEAS](IDEAS.md), and set the seam thresholds.
- [ ] Then try `TWCMap1-Straight.png` for lettering and located content.

**Acceptance:** manual: the finished kittens PNG is 2560x1920 and the user
judges the seam acceptable by looking at the preview and crops; findings
written to the design.

## Later (optional/deferred)

- Submission to the distribution repository and its release build (how that
  repository packages scripts is unverified).

## Open Questions

- None beyond those in [DESIGN-packaging.md](DESIGN-packaging.md).
