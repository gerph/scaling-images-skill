---
name: scaling-images
description: Enlarge an image far beyond an image generator's size limit, tile by tile, keeping style and joins consistent. Use when scaling up, upscaling or increasing the resolution of artwork, maps or photographs with a generator.
metadata:
  author: Charles Ferguson (Gerph)
license: MIT
---

# Scaling images

Enlarges an image beyond what an image generator can draw in one go. The image is
built as a canvas of tiles: each tile is redrawn by the generator with the already
accepted high-resolution pixels beside it as context, a blocky enlargement of the
part not yet drawn, marker lines showing where to start, and a written description
that restates the style and content every time. Scripts do all the geometry,
compositing, checking and bookkeeping; you describe the image and drive the generator.

## When to use

- The user wants a picture made bigger (a factor, or a target resolution) than a generator can produce.
- Aspect ratio must stay the same (padding, cropping and aspect-ratio changes are not supported yet).

Prerequisites: Python 3.9+, Pillow and numpy. Check with
`python3 scripts/scale_image.py setup --check`; install with `setup` or
`setup --venv ~/.scaling-images-venv` (recorded and used automatically afterwards).
If a command prints "Missing Python packages", run the install command it gives.

In this file `scale` means `python3 <skill directory>/scripts/scale_image.py`.

## Workflow

1. **Look at the original, unmodified, at full size.** Write `description.md` in a new
   work directory following [references/description-format.md](references/description-format.md):
   composition and style (including the colour grade), content with located bounding boxes, and source artefacts.
2. **Ask the user to review the description** (and the box overlay, if useful). They may change
   any element. Do not go on until they approve. Never edit it again during the run: if it must
   change, the user does it, and the scripts pause the run.
3. **Ask whether the picture is to be restyled** (for example "as heavy oil paint"). If so, put it in the
   description and pass `--no-structure` to `init`. **Get the scale.** A factor or a target resolution. If the target's aspect ratio differs from
   the source's, stop: that is not supported yet.
4. **Choose the generator profile** from the tool you actually have
   ([references/generator-profiles.md](references/generator-profiles.md)): `gpt-image-2-api`
   (the size you ask for is honoured), `codex-builtin` (size is ignored), or `custom`.
5. `scale init SOURCE --factor N` (or `--target WxH`) `--profile P --work DIR`. It plans the tiles
   and refuses impossible requests with the reason.
6. If the size is not honoured, `scale probe --work DIR` and follow it, then `probe --result FILE`;
   re-run `init --force --tile N` if it recommends a smaller tile.
7. **Loop until done:**
   1. `scale next --work DIR` prints the instructions for the next tile and writes its input image.
      Follow them exactly: give the input image (and, if the tool takes several images, the
      reference images) to the generator and save the result where it says.
   2. Look at the result before accepting it. Then `scale accept --work DIR`.
      Exit status 0 = accepted; 5 = accepted with warnings (read and report them); 2 = rejected
      (regenerate from the same input); 3 = paused, see below.
   3. Look at the 1:1 seam crops it names, and tell the user about any visible join. A bad
      tile is cheapest to redo before the next one is made.
8. `scale preview --work DIR` at any point for a preview and the per-seam report; show the user.
9. `scale finish --work DIR` writes the final PNG at exactly the target size.

## Rules

- **Description changed** (exit status 3, "PAUSED"): stop and ask the user which they want:
  revert it, `description --adopt` (from the current tile on), or `description --adopt --redo-from TILE --yes`.
  Do not choose for them.
- **Redo**: `scale redo TILE` lists the tiles that would be discarded (the tile and every later one that
  used its pixels). Tell the user; only after they agree run it again with `--yes`.
- Never hand-edit `state.json`, the canvas or the mask.
- Do not invent content the description does not list. Do not let the generator redraw or move the
  finished context.
- Resuming: every command needs only `--work DIR` (or run it in that directory); `status` shows where it is.
- The scripts never call a generator. If a tool does not accept several images, use just the input image.

## References

- [references/description-format.md](references/description-format.md): what to put in the description, the JSON block, a worked example.
- [references/generator-profiles.md](references/generator-profiles.md): the generator size rules, how to pick a profile, the Codex built-in size problem.
- [references/seams.md](references/seams.md): what the seam numbers mean and what to do about visible joins.
