# Plan: Description

Part of the [implementation plan](OVERVIEW.md#implementation-plan). Implements
[DESIGN-description.md](DESIGN-description.md).

## Dependencies

- Depends on: the packaging skeleton ([PLAN-packaging.md](PLAN-packaging.md)
  Stage 1).
- Blocks: [PLAN-workflow.md](PLAN-workflow.md) Stage 2 (instructions).
- Independent of: [PLAN-tiling.md](PLAN-tiling.md) Stages 1 to 3 (shares no
  files; takes tile rectangles as plain numbers).

## Stages

### Stage 1 — Parse and hash

- [ ] `description.py`: `load(path)` reads `description.md`: the prose, and the
      fenced `json` block holding `content` items
      (`name`, `note`, `box` = `[x0, y0, x1, y1]` as fractions).
- [ ] `description_hash(text)` normalising line endings and trailing spaces.
- [ ] Clear errors for a missing block, a box outside 0 to 1 and an empty
      description.

**Acceptance:** `pytest tests/test_description.py`: a sample description loads;
a trailing-space edit leaves the hash unchanged; a word change alters it.

### Stage 2 — Classify items against a tile

- [ ] `classify(items, tile, scale, source_size)` returning three lists:
      *in context* (box inside the accepted area), *new* (box overlaps the
      new region) and *outside*; an item straddling a seam is listed as *new*
      and flagged as "continues from the context".

**Acceptance:** `pytest tests/test_description.py::test_classify` with boxes
placed inside, across and outside a 2560x1920 two-tile layout.

### Stage 3 — Review overlay

- [ ] `overlay(source, items)` writing the original with the labelled boxes
      for the user to check.

**Acceptance:** manual: run on `TWCMap1-Straight.png` with a hand-written
description and open the PNG with `host-open`; the boxes sit on the features
they name.

### Stage 4 — Description template and guidance

- [ ] `references/description-format.md` in the skill: the section checklist
      from the design (including source artefacts and detail scale), a worked
      example for `KittensSmall.jpg`, and the JSON block format. Written after
      reading the repository's skill-writing guidance.

**Acceptance:** a fresh agent given only this file can write a description that
passes `load`; checked on `KittensSmall.jpg` in the trial.

## Later (optional/deferred)

- Nothing.

## Open Questions

- None.
