# Changelog

## 0.1.0 - unreleased

- `preview` shows each accepted tile's lightness against the original as a grid and lists drifted tiles; `accept` warns
  when a tile's colour has drifted (not when restyling). On the 60-tile job it flags exactly the four washed-out tiles.

- Large images no longer drift in colour: each tile's broad colour is anchored to the original's (`init --anchor`,
  on unless restyling) and the seam colour correction fades with distance from the seam. A 60-tile job had drifted
  to 2.1x the original's lightness by its third row; replayed on its stored tiles, every tile stays within 0.92 to
  1.04x and the worst seam score fell from 3.41 to 1.87.

- `init --enlarge smooth` shows the not-yet-drawn part of each tile input as a smooth (bicubic) enlargement instead of
  blocky nearest-neighbour, for hard-edged art (found when a cartoon's first tile kept the staircase edges of its
  blocky input while later tiles, matching smooth artwork, did not). The tile instructions now say that stair-stepped
  edges are artefacts of the enlargement and to draw clean edges, unless the description says the pixel look is style.

- Sources with transparency: `init` stops and asks for `--alpha composite` (flatten onto `--background`, default white)
  or `--alpha keep` (generate on the backdrop, then restore the original alpha scaled up, with the backdrop mix removed
  from edge pixels, as an RGBA PNG). `--restyle` renders the picture in a Target style from the description, with its own
  first-tile instructions and the structure check off. The structure check no longer gives NaN for flat tiles.

- `check` runs every `accept` validation on a candidate result without merging it, so an agent can test attempts
  before committing one. The tile instructions now say to keep the framing exactly, to add no border, to draw nothing
  that lies outside the tile and not to flatten textured areas into smooth colour.

- Fix a colour step along the vertical seam of tiles that have both a left and a top seam: the top-seam colour
  correction is now applied across the same columns as the left one (found on a real wall, 19 grey levels reduced to ~0).

- Structure check: warns when a tile's edge layout drifts from the original (found when a generator moved a wall edge);
  `init --no-structure` for deliberate restyling.

- Feathering: each seam is cross-faded over `--feather` pixels (default 128) of the context, hiding residual colour and line
  mismatches (replayed on the real trial, the seam disappears); `redo` restores the blended pixels. The tile instructions
  and description guidance now stress keeping the colour grade.

- Tone correction now follows a vertical (or horizontal) colour gradient, found in a real trial where the
  generator changed the sky colour from top to bottom; seam warnings start at ratio 2.5; `probe` notices when
  a generator delivers more than was asked; the `codex-builtin` profile defaults to a 1248 tile.

- First version: tiled enlargement driven by an agent, with a description of style and content,
  generator profiles, marker-line context, tile validation, seam measurement, redo, resumable state,
  description-change pause and a dependency installer.
