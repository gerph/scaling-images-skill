# Description

Part of [Image scaling skill](OVERVIEW.md). Feeds [Tiling](DESIGN-tiling.md)
(positions) and [Workflow](DESIGN-workflow.md) (the text repeated in every
tile's instructions).

## Decisions

- Before any scaling the agent looks at the original, full-size, unmodified
  image and writes a description in two separate sections, then asks the
  user to review it. Nothing is generated until the user approves it; the
  user may change any element.
- **Section 1: composition and style** (how the picture is made). The agent
  covers each of these, writing "none" or "not applicable" rather than
  omitting one:
  - Medium (paint, crayon, pencil, collage, clay, embroidery, knitting,
    tile, inlay, metalwork, relief/embossing and so on).
  - Technique (stroke length and direction, dabbing, cut paper,
    pointillism, hatching, ...).
  - School or stylistic form (photographic, cubist, surrealist, flat
    iconic, ...).
  - Focus and emphasis: blur or depth-of-field, areas that are
    deliberately accurate versus cartoon or iconic.
  - Lighting, shadow direction and colour palette, including any
    deliberately restricted palette.
  - Typography: typeface style, case, weight, how text is rendered (inlaid,
    embossed, painted) and what it is set against.
  - Flourishes to retain (borders, ornaments, textures).
  - **Detail scale.** For every repeating or textural element (waves, fur,
    brickwork, foliage, brush strokes, grain, stitches) whether its unit
    keeps its size *relative to the picture* and gains finer, more accurate
    detail when enlarged (the default), or should itself grow. This stops
    an enlargement merely magnifying and smoothing the original's detail.
  - **Source artefacts** (see below).
- **Section 2: content** (what matters in the picture): frame or border,
  places and labelled features, arrows and connecting lines (and how
  straight they should be), keys/legends/scale bars/compass, shadow and
  light effects that carry meaning, and any text with its exact wording.
- **Source artefacts.** The description states what the source format
  introduced that is *not* part of the artwork, and what to do about it:
  - JPEG: DCT block/quantisation noise, ringing, and chroma (YCbCr)
    subsampling bleed are to be removed, not reproduced.
  - Icons/low-colour/GIF sources: say whether dithering is a style to be
    kept (redrawn at high resolution, not as big pixels) or an artefact to
    be replaced by accurate colour; say whether a restricted palette (for
    example only primary colours) is to be kept.
  - Upscale blur, screenshot compression and watermark are handled the same
    way: named, and marked keep or discard.
- **Located content.** Each content item carries a name, a one-line note and
  an approximate bounding box (`x0,y0,x1,y1`, as fractions of the original).
  This is how the script works out, for each tile, which items are
  *already drawn in the context*, which are *to be drawn in this tile's new
  area*, and which lie *outside the tile*. Agreed by the user, who wants
  positions kept right and no feature duplicated into several tiles. Boxes
  need only be rough; the user reviews them on an overlay of the original
  produced by the script.
- Whatever the user changes during review is recorded in the description
  file itself, so every later tile reads the amended version.
- The description is stored as a file in the work directory. The state file
  holds its hash, not a copy; if it changes during a run the run pauses (see
  [Workflow](DESIGN-workflow.md)).

## Open Questions

None at present.

## Proposals

- **Format.** `description.md` with the two sections as prose for the user to
  read and edit, plus a `content` block (YAML or JSON) holding the located
  items. The block is parsed by the scripts; the prose is passed through
  as is.
