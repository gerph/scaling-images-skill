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
