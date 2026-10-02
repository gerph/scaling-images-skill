# Changelog

## 0.1.0 - unreleased

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
