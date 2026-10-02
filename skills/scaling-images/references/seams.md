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
- **Checks**: a leftover marker line, a wrong shape, or a context that no longer matches rejects the tile.

If a seam is visible: redo that tile now (`redo TILE`, before later tiles depend on it), asking the
generator again from the same input. Do not accept a bad tile and carry on.
