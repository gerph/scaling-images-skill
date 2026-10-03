# Seams

After each `accept`, the script prints, for each new seam, the mean pixel difference *across* the join,
the difference between neighbouring pixels *near* the join, and their ratio. A ratio near 1 means the
join is as smooth as the picture; over 2.5 is flagged as visible. The number is a guide only: it cannot
see a slight colour step or a slightly mismatched line, so always look at the crops. A 1:1 crop centred on each seam is
saved in the tile's directory (`seam-left.png`, `seam-top.png`). Always look at them.

Built in, applied automatically before the hard cut at the marker line:

- **Alignment**: if the generator shifted the context, the offset is measured and corrected (warned about).
- **Tone correction**: generators often shift colour and contrast differently from top to bottom, leaving a
  colour step down the seam (visible in plain sky). The per-row (left seam) or per-column (top seam) difference
  between our context and the generator's copy beside the seam is smoothed and added to the new region.
  Turn off with `init --no-tone`; alignment with `--no-align`.
- **Anchoring to the original** (on by default; `init --anchor off` turns it off; `auto` leaves it off when
  restyling): matching each tile only to its neighbour lets small errors add up, so over a large image every
  step right or down drifts lighter or tinted. Each returned tile's broad colour (blurred over about a sixth
  of the tile) is multiplied back towards the original's, so features smaller than that keep the generator's
  rendering and the large-scale colour stays where the original has it. Found on a 60-tile job where one row
  ended 2x lighter than the original.
- **Seam colour correction fades with distance** (about an eighth of the tile): an error measured at the seam,
  such as bright content that differs between the two copies, must not spread across the whole tile.
- **Feathering** (on by default, `init --feather N`, 0 turns it off): over N pixels (default 128) on the context
  side of each new seam the canvas is cross-faded into the generator's copy of the context, which is continuous
  with the new region. A leftover colour step or line mismatch becomes a gradual change instead of a join. The
  blended pixels are saved so `redo` can restore them. Seam numbers are measured before feathering, so they say
  how visible a hard cut would have been.
- **Structure check** (on by default; `init --no-structure` turns it off): compares the edge layout of each new
  region with our blocky enlargement of the original, ignoring colour, and warns when a tile's median
  correlation is below 0.5 (an edge has moved, content has been invented or lost). It never rejects. Turn it
  off when the user has asked to restyle the picture, since a changed style changes the edges; when a
  description is adopted part-way through a run, it is skipped for the first tile after the change.
- **Checks**: a leftover marker line, a wrong shape, or a context that no longer matches rejects the tile.

If a seam is visible: redo that tile now (`redo TILE`, before later tiles depend on it), asking the
generator again from the same input. Do not accept a bad tile and carry on.
