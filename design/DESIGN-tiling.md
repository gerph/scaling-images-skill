# Tiling

Part of [Image scaling skill](OVERVIEW.md). Uses the positions in
[Description](DESIGN-description.md); produces the inputs and consumes the
outputs described in [Workflow](DESIGN-workflow.md).

## Decisions

### Scale

- The user gives either a **factor** or a **target resolution** (W x H).
  Factor: target = round(source x factor). The target must be met exactly.
- For now the aspect ratio must be unchanged (to within the rounding of the
  target). If a target resolution has a different aspect ratio the script
  stops with an error that says so; padding and aspect-ratio expansion are
  deferred (see [IDEAS](IDEAS.md)). The scale is then uniform on both axes
  and may be non-integer.

### Tile size and windows

- Tile size T defaults to 2048 and is a parameter, which a generator
  profile (see [Workflow](DESIGN-workflow.md#generators)) can lower or raise
  to what the generator really delivers. Every generation request
  is a *window* onto the large canvas, at most T x T. If the target is
  smaller than T on an axis the window is clamped to the target on that
  axis; if both axes fit, one generation is made and no seams exist.
- **Window dimensions respect the generator's rules** (for the first
  target, gpt-image-2: each edge a multiple of 16, long edge no more than
  3840, aspect ratio no more than 3:1, 655,360 to 8,294,400 pixels in total).
  A window edge that is not a multiple of 16 is grown to the next multiple,
  towards the already-accepted side where there is one (a larger context, not
  a different slice). Where there is no accepted side (a single-tile axis, or
  the first tile) the extra rows or columns are filled by repeating the edge
  pixels and are cropped from the result. A window outside the pixel
  limits is a configuration error reported by `init`.
- Tiles are generated in row-major order, left to right, top to bottom.
- The script keeps a **canvas** at target size holding the accepted
  high-resolution pixels. A tile's input is the window cut from the canvas,
  with every not-yet-accepted pixel filled from the corresponding region of
  the original enlarged with **nearest-neighbour** (so it is visibly
  blocky).
- A **context** strip of accepted pixels lies to the left of and/or above
  the unknown area. Default one third of the window (`context`, parameter).
  Minimum context is a parameter that defaults to 256 px at T = 2048 (T / 8);
  the user originally suggested a floor of 20 and then thought 400 might be
  excessive and delegated the choice (agent-chosen, because a seam can only
  be matched if the generator can see a few hundred pixels of both the
  texture and the layout beside it).
- **Marker lines** are drawn over the first few pixels of the unknown region:
  a vertical line at its left edge (tiles in columns after the first) and a
  horizontal line at its top edge (tiles in rows after the first); tiles
  after the first in the second or later row have both. Default width 6 px
  (parameter; "a few pixels" per the user, since 1 px would be lost when the
  generator downsamples its input). Red by default; the colour used is the
  one least present in the original (so a largely red image gets another).
  The instructions say to redraw the marked line and everything to its
  right/below, matching the content on the other side.
- The first tile has no context and no marker lines: it is the top-left of
  the original, nearest-enlarged, and the agent is told to redraw it at higher
  quality.
- Because context comes from the canvas, the top strip for a tile in the
  second or later row spans the full window width, including the area above
  the unknown region to the right, accepted in the previous row.

### Slice sizes

- A **slice** is the width (or height) of the new region a tile contributes.
  With context C, a slice after the first is at most cap = T - C.
- The **first** slice of an axis takes the full T, since it has no seam to
  match. The number of slices n is the smallest that covers the axis:
  n = 1 + ceil((L - T) / cap). The remaining n-1 slices are made equal.
- **Not disproportionate.** If an equal remaining slice r = (L - T)/(n-1)
  is under half of cap, the first slice is not made full: all n slices are
  made equal at L/n. The tile count is the same, and L/n <= cap is
  guaranteed in that case (the script asserts it). A slice is never below the
  minimum slice (parameter, default T / 4 = 512, a few hundred px).
- Worked example (T = 2048, C = 683, cap = 1365). `KittensSmall.jpg` at 4x is
  2560 wide: n = 2, r = 512 < 683, so both slices are 1280 (the second
  tile's window starts at 1280 - 768 = 512 and its context is 768 px). 6144 wide:
  n = 4, r = 1365 >= 683, so slices are 2048, 1365, 1366, 1365. The height 1920
  fits in one window, so one row.

### Accepting a tile and stitching

- When a generated tile is accepted only the **new** (unknown) region is
  taken into the canvas (subject to the seam treatment below); the generator's
  copy of the context is discarded. When the last tile is accepted the
  canvas *is* the final image, written as PNG.

### Seams

The user wants to find out how seams can be influenced. The generator may
shift, rescale or redraw the context it is given, so a hard cut at the marker
line depends on its fidelity. Treatments, cheapest first, each applied to the
generated tile before it is merged and each switchable by parameter:

1. **Hard cut** at the marker line (the baseline).
2. **Alignment correction.** Measure the offset (and any small scale
   difference) between the generator's copy of the context and the canvas, using
   correlation over the context region, and warp the generated tile to
   match before cutting. Reject the tile if the offset is large.
3. **Tone matching.** Adjust the new region's low-frequency colour and
   brightness so it meets the canvas across the seam (match the mean and
   spread in a band either side), because a generator may drift in tone
   without moving anything.
4. **Feather.** Blend across a narrow band using the generator's copy of the
   context, so a residual difference becomes a gradient rather than a line.
5. **Minimum-difference seam.** Instead of a straight cut, find the path
   through the context overlap where the canvas and the generated copy
   differ least (as in image quilting), which hides the join in texture.
6. **Seam repair tile.** After assembly, regenerate a band centred on a bad
   seam with known pixels on both sides and a marked band between them. This
   is the same mechanism as the patch redo in [IDEAS](IDEAS.md).

The script measures every seam (difference across the join compared with
nearby pixels) and reports it; the user sees the numbers in the review aids.

## Open Questions

- **Which seam treatments to build first.** Proposed below; the choice is
  decided by experiment on `KittensSmall.jpg`.
- **Window shape.** gpt-image-2 accepts non-square sizes within its rules
  (researched, see [Workflow](DESIGN-workflow.md#generators)), so a clamped
  window such as 2048 x 1920 is allowed there; the built-in Codex tool may not
  honour the size, which is handled by the Workflow design.

## Proposals

- Build treatments 1 to 3 and the seam measure first, then see whether 4 to 6
  are needed.
