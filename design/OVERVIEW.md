# Image scaling skill

## Goal

A skill that lets an agent enlarge an image far beyond what an image
generation tool can produce in one go, while keeping the style of the
original constant and avoiding visible joins. Asking a generator to draw an
image "in tiles" fails because neighbouring tiles disagree at their edges
and the style drifts. This design instead builds the large image
progressively, tile by tile, with each tile generated *with the already
accepted high-resolution pixels beside it as context*, a crude enlargement of
the not-yet-generated part, and a written description that re-asserts the
style and the content every time. Python scripts supplied with the skill do
all the geometry, compositing, state tracking and checking; the agent
describes the image, drives the generator and relays the user's decisions.

Author: Charles Ferguson (Gerph). Licence: MIT.

## Scope

**In scope:**
- Analysing a source image into a reviewable description (style and content).
- Choosing a scale by factor or by target resolution, **where the aspect
  ratio is unchanged**.
- Planning a tile grid, producing each tile's input image and instructions,
  validating each generated tile, and stitching the final PNG.
- Resumable progress through a state file.
- PNG output; handling JPEG and other source-format artefacts.
- Review aids (preview and seam report).

**Out of scope (for now):**
- Changing the aspect ratio, including padding (see [IDEAS](IDEAS.md)).
- Calling any particular image generator (the agent uses whichever tool the
  session provides; the scripts are generator-agnostic; a direct API back end
  is in [IDEAS](IDEAS.md)).
- Making images smaller; non-raster (vector) sources.

## Contents

**Designs:**

- [Description](DESIGN-description.md) — what the agent records about the
  image's style and content, and how the user reviews it.
- [Tiling](DESIGN-tiling.md) — scale, tile grid, context regions, marker
  lines, seam treatment and final stitching.
- [Workflow](DESIGN-workflow.md) — the scripts' commands, state file, the
  instructions given to the agent, validation, review aids and failure paths.

- [Packaging](DESIGN-packaging.md) — repository layout, the skill's files,
  testing and distribution through an agent-skills repository.

**Plans:**

- [Packaging](PLAN-packaging.md) — skeleton, entry point and setup, `SKILL.md`,
  package test and the real-generator trial. **Stage 1 first; everything else
  depends on it.**
- [Tiling](PLAN-tiling.md) — geometry, canvas, merge, seam measures.
- [Description](PLAN-description.md) — parsing, classification, overlay.
- [Workflow](PLAN-workflow.md) — fake generator, state, `init`, `next`,
  `accept`, redo and the rest of the commands.

**Other:**

- [IDEAS](IDEAS.md) — aspect-ratio expansion; progressive enlargement;
  direct image API back end; patch redo.

## Open Questions

None at present beyond those inside the area documents.

## Test material

- `KittensSmall.jpg` (640x480, JPEG, 4:3): first test case. A photograph of
  four kittens on a wall with soft-focus hills behind; it exercises JPEG
  artefact handling, a shallow depth of field and fur/stone texture. At 4x it
  is 2560x1920, which needs two columns and one row of tiles at T = 2048.
- `TWCMap1-Straight.png` (1536x1024, RGB): a relief-style fantasy map with
  lettering, a key and a frame; a later test for text and located content.
- Larger images follow once the process works.

These sit in the repository root and are not part of the skill.

## Implementation plan

**Shared conventions** - choices every area's stages rely on:

- **Where new code lives** - `skills/scaling-images/` (the shipped skill:
  `SKILL.md`, `scripts/scale_image.py`, `scripts/scaling_images/`,
  `references/`); `tests/` and `design/` are not shipped. The layout mirrors
  the one used by skills in `gerph/riscos-agent-skills` (checked against its
  README only).
- **How dependencies are installed** - Pillow and numpy through
  `requirements.txt`, installed by the skill's own `setup` command (optionally
  into a venv). Python 3.9 or later. Test-only dependency: pytest (installed
  here: Python 3.12.3, numpy 1.26.4, Pillow 12.2.0, pytest 9.1.1).
- **Tests** - pytest, `pytest tests/`; no test calls a generator or the
  network. The fake generator in `tests/` stands in for one.
- **Description format** - prose plus a fenced JSON block (no YAML).
- **Commits are one per stage**, using the stage's short description as the
  subject, on a feature branch (never `master`), adding files explicitly. The
  design is already committed on branch `design`.
- **Docs/changelog land with the stage** that changes user-visible behaviour.
- **Work directory and test images** are never committed (they are binary
  output); the test images stay in the repository root, outside the skill.

**Waves** - sets of stages that can proceed at the same time because none
touches files or runtime state another in the wave depends on. Waves are
sequential: start one only when every stage in the previous one is committed.

1. **Wave 0** - Packaging Stage 1 (skeleton, entry point, setup).
2. **Wave 1** - Tiling Stages 1 to 3 and Description Stages 1 and 2. These two
   tracks share no files and could be done by separate subagents, but the gain
   is small and they are best done in one thread unless asked otherwise.
3. **Wave 2** - Workflow Stages 1 to 3 (fake generator, `init`, `next`,
   `accept` with the hard cut): the first end-to-end run, with the fake
   generator, on `KittensSmall.jpg`.
4. **Wave 3** - Tiling Stage 4, Workflow Stages 4 to 6 and Description Stages
   3 and 4.
5. **Wave 4** - Packaging Stages 2 to 4.
6. **Wave 5** - Packaging Stage 5 (the real trial); its findings may reopen
   the design.
