# Plan: Tiling

Part of the [implementation plan](OVERVIEW.md#implementation-plan). Implements
[DESIGN-tiling.md](DESIGN-tiling.md).

## Dependencies

- Depends on: the packaging skeleton ([PLAN-packaging.md](PLAN-packaging.md)
  Stage 1) for the module location and the test setup.
- Blocks: [PLAN-workflow.md](PLAN-workflow.md) Stages 2 onwards (they consume
  the geometry and canvas modules).
- Independent of: [PLAN-description.md](PLAN-description.md) Stages 1 and 2
  (no shared files; description only needs tile rectangles as plain numbers).

All code is in `skills/scaling-images/scripts/scaling_images/`; tests in
`tests/`. These modules must not import the CLI, so the geometry can be
tested alone.

## Stages

### Stage 1 — Geometry

- [ ] `geometry.py`: `target_size(source, factor=None, target=None)` (exact
      target; raises `AspectRatioError` if the aspect ratio changes beyond
      rounding).
- [ ] `plan_axis(length, T, context, min_slice)` returning the slice list per
      the "Slice sizes" rules (full first slice; equal remainder; the
      "under half of cap" fallback to all-equal; asserts L/n <= cap there).
- [ ] `plan_grid(target, profile)` returning tiles in row-major order, each
      with: accepted rectangle, window rectangle (rounded up to the profile's
      multiple, towards the accepted side), context sizes, which marker lines
      apply, and padding (edge-repeat) amounts where there is no accepted
      side.
- [ ] `dependents(grid, tile)`: later tiles whose windows overlap the tile's
      accepted rectangle.
- [ ] Tests for every worked example in the design.

**Acceptance:** `pytest tests/test_geometry.py` passes, including: 2560 wide
gives slices 1280 and 1280 with the second window starting at 512; 6144 wide
gives 2048, 1365, 1366, 1365; 1920 high at T = 2048 gives one row with a window
height of 1920; no slice under the minimum slice for any length from 1 to
10000 and any T in {1024, 2048, 3072}; windows always satisfy the multiple-of-16
rule and stay within the pixel limits or raise.

**Notes:** Use integers throughout; distribute remainders so slice widths
differ by at most 1. Context default is round(T / 3), minimum context T / 8,
minimum slice T / 4, marker width 6 (all arguments, not constants).

### Stage 2 — Canvas and tile input

- [ ] `canvas.py`: a canvas at target size (RGB, stored as PNG in the work
      directory) with an accepted mask, saved and loaded.
- [ ] `render_input(source, canvas, tile, scale, marker)`: the window with
      accepted pixels from the canvas and the rest nearest-neighbour from the
      source, edge-padded where the plan says so, with marker lines drawn over
      the first pixels of the unknown region.
- [ ] `choose_marker_colour(source)`: the colour from a short candidate list
      (red, magenta, green, cyan, yellow) least present in the source, by
      distance to the source's pixels.
- [ ] `locator_image(source, tile)`: the original with the tile's footprint
      outlined, plus the plain original copy.
- [ ] Tests on a synthetic gradient source.

**Acceptance:** `pytest tests/test_canvas.py`: the first tile contains no marker
and equals a nearest upscale of the source's top left; a tile in column 1 has a
vertical marker exactly at the first unknown column and nothing of the
unknown region leaks accepted pixels; a tile in row 1 column 1 has both
markers; a mostly-red source gets a non-red marker.

**Notes:** Nearest mapping must use pixel centres (`floor((x + 0.5) / scale)`)
so that a non-integer scale does not shift content across a seam.

### Stage 3 — Merge (hard cut)

- [ ] `merge(canvas, tile, generated)`: resize check is the caller's; copy
      only the new region into the canvas and mark it accepted; keep the old
      pixels until `commit` for redo.
- [ ] Final write of the canvas as PNG.

**Acceptance:** `pytest tests/test_merge.py`: merging a generated image that
equals the ideal result for every tile in order reproduces the ideal image
exactly (pixel for pixel) for 2560x1920 and a 3x3 grid case.

### Stage 4 — Seam measure, alignment and tone matching

- [ ] `seams.py`: `seam_report(canvas, tile)` (difference across the join compared
      with the neighbouring pixel differences); 1:1 seam crop images.
- [ ] `estimate_offset(context_supplied, context_returned)` by correlation on
      downscaled luminance, then refined; `align(generated, offset)`.
- [ ] `tone_match(new_region, canvas, tile)` low-frequency match across the
      seam.
- [ ] Each switchable by an option.

**Acceptance:** `pytest tests/test_seams.py`: a generated tile that is the ideal
tile shifted by 3 px is corrected to under 0.5 px residual; a tone-shifted tile
has its seam measure fall below the threshold after matching; an ideal tile is
left unchanged (within 1 grey level).

## Later (optional/deferred)

- Feather, minimum-difference seam, seam repair tile, patch redo (see
  [IDEAS](IDEAS.md) and the Seams section of the design). Chosen after the
  trial in [PLAN-packaging.md](PLAN-packaging.md) Stage 5.

## Open Questions

- Seam-measure thresholds can only be set from real generator output (Stage 5
  of the packaging plan); Stage 4 ships provisional values.
