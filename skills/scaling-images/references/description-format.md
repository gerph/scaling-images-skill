# The description file

`description.md` is prose for the user to read and edit, plus one fenced `json` block holding
the located content. The prose is given to the generator with every tile; the scripts read the
JSON to say which features are already drawn, to be drawn, or not in a tile.

Look at the whole original, unmodified, before writing it. Write "none" or "not applicable"
rather than leaving a heading out, so the user can see it was considered.

## Section 1: composition and style (how the picture is made)

- **Medium**: paint, crayon, pencil, collage, clay, embroidery, knitting, tile, inlay, metalwork,
  relief or embossing, photograph, and so on.
- **Technique**: stroke length and direction, dabbing, cut paper, pointillism, hatching.
- **School or stylistic form**: photographic, cubist, surrealist, flat and iconic, and so on.
- **Focus and emphasis**: blur or depth of field; areas deliberately accurate versus cartoon or iconic.
- **Light, shadow and palette**: direction of light, colour range, any deliberately restricted palette.
- **Colour grade** (state this carefully; generators drift here and it shows as colour steps at the seams):
  the overall tint or white balance (for example "cool, lilac-grey dusk"), saturation (muted, vivid),
  contrast and tonal range, how bright the sky, lights and darks are, and any smooth gradient that must
  continue across the whole picture (a sky darkening upwards, a vignette). Say what must *not* happen:
  no boosting of saturation or contrast, no "improving" of the grade, no sharpening of intentionally soft areas.
  Name the key colours with plain words and, where it helps, approximate values read from the original.
- **Typography**: typeface style, case, weight, how it is rendered (inlaid, embossed, painted).
- **Flourishes to retain**: borders, ornaments, textures.
- **Detail scale**: for every repeating or textural element (waves, fur, brickwork, foliage, grain)
  say whether it keeps its size relative to the picture and gains finer, more accurate detail when
  enlarged (the default), or should itself grow. This stops enlargement merely magnifying and
  smoothing the original's detail.
- **Source artefacts**: what the file format added that is not part of the artwork, and whether to
  keep or discard it.
  - JPEG: DCT block and quantisation noise, ringing and chroma (YCbCr) bleed are to be removed, not reproduced.
  - Icons, GIFs and low-colour images: say whether dithering is a style to keep (redrawn at high
    resolution, not as big pixels) or an artefact to replace with accurate colour; say whether a
    restricted palette (such as primary colours only) is kept.
  - Upscale blur, compression and watermarks: name each and mark it keep or discard.

## Restyling: the target style

When the user wants the picture rendered in a different style (for example a cartoon as heavy oil paint),
use `init --restyle` and split section 1 in two:

- **Original style (information only)**: how the source is rendered now (outlines, flat fills, shading). It
  tells the generator what *not* to copy.
- **Target style (apply this)**: the medium, technique, brushwork, texture, lighting and colour treatment the
  result must have, in the same detail as section 1 above (stroke size and direction, impasto, canvas weave,
  how edges and highlights are painted, how colours are mixed). Say how far to go ("heavy, visible brushstrokes;
  keep every shape and its place").

What carries over from the original is section 2: the subject, layout, shapes, positions and the identity of each
colour (a red gem stays red). Write section 2 as what is in the picture, not how it is drawn, so that it holds in any
style. Typography and text keep their exact wording, but may take the target style's rendering.

## Hard edges and how the enlargement is shown

Each tile's input shows the not-yet-drawn part enlarged. The default is blocky nearest-neighbour, which tells the
generator plainly that it must redraw; that works well for photographs and textured art. For hard-edged art
(cartoons, icons, line art) the staircase edges can be copied into the first tile, which has no finished
artwork beside it to match. Use `init --enlarge smooth` there (a smooth, blurry enlargement with no staircase). If
a pixel or dithered look is part of the style, say so in the source artefacts item and keep the default.

## Transparent backgrounds

If the source has transparency, `init` stops and asks for a choice: `--alpha composite` (put the picture on a plain
colour and keep the result opaque) or `--alpha keep` (generate on a plain backdrop, then restore the original alpha,
scaled up, for an RGBA result). `--background` sets the colour (default white). Say in the description that the
background is transparent and must stay plain; the tile instructions repeat that.

## Section 2: content (what matters in the picture)

Frame or border, labelled places and features, arrows and connecting lines (and how straight they
should be), keys, legends, scale bars and compasses, shadows and lighting that carry meaning, and
all text with its exact wording.

## The content block

A fenced `json` block with a `content` list. Each item has a `name`, a one-line `note` and a
rough `box` `[x0, y0, x1, y1]` as fractions (0 to 1) of the original, left to right and top to bottom.
Boxes need only be approximate. Every entry in section 2 that has a place should have one.

## Worked example (a photograph)

    # Composition and style
    Medium: photograph, taken at dusk, soft focus; the kittens are in sharper focus than the hills.
    Technique: not applicable. School: naturalistic snapshot.
    Light: low, cool, even; muted lilac-grey sky; warm browns for fur.
    Colour grade: cool, slightly desaturated dusk; sky a soft lilac-grey that is a little darker towards the
    top; low contrast with lifted blacks. Do not increase saturation or contrast, or add a warm or blue cast.
    Typography: none. Flourishes: none.
    Detail scale: fur keeps its size relative to the cats and gains individual hairs; stone keeps
    its grain; hills stay soft.
    Source artefacts: JPEG blocking and chroma bleed in the sky and wall; discard them.

    # Content
    Four kittens sit on a white wall in the lower middle; behind them a farmland valley, then hills,
    then sky with power lines. A white pillar is at the far left.

    ```json
    {"content": [
      {"name": "kittens", "note": "four kittens: ginger tabby, white, grey, dark tabby", "box": [0.15, 0.4, 0.75, 0.75]},
      {"name": "wall", "note": "white wall, foreground", "box": [0.0, 0.7, 1.0, 1.0]},
      {"name": "pillar", "note": "white pillar at left", "box": [0.0, 0.0, 0.1, 0.8]},
      {"name": "hills", "note": "soft blue-grey hills", "box": [0.1, 0.22, 1.0, 0.42]},
      {"name": "power lines", "note": "two thin lines across the sky", "box": [0.1, 0.0, 1.0, 0.15]}
    ]}
    ```
