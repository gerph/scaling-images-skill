# Workflow

Part of [Image scaling skill](OVERVIEW.md). Implements
[Tiling](DESIGN-tiling.md) using the text from
[Description](DESIGN-description.md).

## Decisions

- The scripts are Python (Pillow; numpy if needed), shipped with the skill,
  and are generator-agnostic: they produce an input image and written
  instructions per tile and accept a result image back; the agent calls
  whatever image generator the session provides.
- Output files are PNG. A JPEG (or other lossy/low-colour) source is
  converted on load; its artefacts are covered by the description.
- Progress is held in a **state file** in a work directory: the parameters
  (source, target size, T, context, minimum slice, marker colour and width,
  seam options), the tile grid, which tiles are accepted, the description
  file reference, and the current tile. The canvas is stored as a PNG in the
  work directory, so a later session resumes where it stopped.
- Each step: the agent calls the script; the script writes the tile's input
  image and prints instructions (what to redraw, at what resolution, which
  part of the original this is, the style and content from the description,
  and where to save the result). The agent generates the tile, saves it there,
  and calls the script again, which validates and accepts the tile and
  then prepares the next.
- **Position and content in instructions.** Each tile's instructions list
  its content items in three groups, from the located items in the
  description: *already drawn in the context (do not repeat or move)*, *to be
  drawn in the new area*, and *not in this tile*. Each tile is told the
  fraction of the original it covers.
- **Reference images.** The script also writes the whole original and a small
  locator image (the original with the tile outlined) next to each tile's
  input. The instructions tell the agent to supply them to the generator
  where the tool accepts several input images, and to ignore them otherwise.
  Their usefulness depends on the generator.
- **The workflow is agent-driven only.** The scripts never call a generator
  (the user wants the skill to work with any system; a direct API back end is
  recorded in [IDEAS](IDEAS.md)).
- **Editing the description mid-run pauses the run.** The state file records
  a hash of the description (line endings and trailing spaces normalised, so
  trivial edits do not count) taken when the run starts and recorded with each
  accepted tile. Every command except `status` and `preview` compares it
  first; on a mismatch it makes no change, exits with a distinct non-zero
  status and prints a message telling the agent to stop and ask the user. The
  user may have changed it on purpose to make a stylistic effect. The message
  gives the choices:
  1. *Revert* the description (the run continues unchanged).
  2. *Adopt* the change from the current tile onwards
     (`description --adopt`): the new hash and the tile it starts at are
     recorded; later tiles use the new text. Because the style will
     legitimately differ across the seam, style-sensitive seam checks (tone
     matching, context correlation) are reported as warnings, not rejections,
     for the first tile after the change, and the seam report notes the
     change.
  3. *Redo* from a chosen tile with the new description
     (`redo --from <tile>`), which discards the later accepted tiles.
  The agent must not edit the description file itself during a run; only the
  user's request leads to an edit, and then the script is the arbiter.
- **Redo.** `redo <tile>` discards the tile and every *dependent* tile: any
  later tile (in generation order) whose window overlaps the redone tile's
  area, because its context came from those pixels. `redo` lists the
  dependents and asks for confirmation before discarding. The old pixels
  stay in the canvas until the redo is accepted. Redoing the most recently
  accepted tile therefore costs nothing extra. The user's view is that most
  of the answer is finding problems early.
- **Early checking.** `accept` writes a 1:1 crop of each new seam (and of the
  corner where a row meets the one above) next to the tile, with the
  numbers from the seam measure. The agent looks at the crop and the user is
  shown it; a tile is only *kept* when `next` is called after that, so a bad
  tile is caught while it has no dependents.
- **Review aids** (command `preview`, also run by `finish`): a downscaled
  preview of the canvas so far, an overlay of the tile boundaries and seams, and a
  per-seam report (see Seams in [Tiling](DESIGN-tiling.md)). The user can
  look at these at any point.

## Generators

The first generator will be Codex's image generation, driven by the agent.
Facts, researched on 2026-10-02 from public sources (not tested here; they
change, so the skill treats them as defaults for a *profile*, not as truth):

- **gpt-image-2 through the Images API or the Codex CLI** accepts any size
  with: each edge a multiple of 16, maximum edge no more than 3840 (some
  sources say less than 3840, so 3824 is the safe maximum), aspect ratio no
  more than 3:1, total pixels from 655,360 to 8,294,400. 2560x1440 is described as
  the reliable upper bound. Sources:
  [prompting guide](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide),
  [launch notes](https://docs.apiyi.com/en/news/gpt-image-2-launch),
  [Foundry notes](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/introducing-openais-gpt-image-2-in-microsoft-foundry/4500571).
  This matches the limits supplied by the user.
- **The built-in Codex `image_gen` tool does not expose size.** Its tool
  surface is only `{type: image_generation, output_format: png}`
  ([openai/codex#19175](https://github.com/openai/codex/issues/19175)), and the
  OAuth-backed Codex path has been reported to ignore `size` and `quality`
  and return smaller images, from 1024x1536 to about 1693x929 (the user's
  1672x941), while still reporting success
  ([openai/codex#28723](https://github.com/openai/codex/issues/28723)). The
  `size=auto` note the user has is consistent with this. The CLI fallback
  with an explicit size and an API key is the reported way to get
  deterministic dimensions.

Consequences for the design:

- A **generator profile** holds the rules (maximum edge, multiple, aspect
  limit, pixel limits, and *whether the requested size is honoured*) and a
  default T. Profiles supplied: `gpt-image-2-api` (honours size), `codex-builtin`
  (does not; the delivered size is learnt by probing), and `custom`
  (all rules given on the command line). The agent chooses the profile by
  which tool it actually has in the session; the scripts cannot detect it.
- Where size is not honoured the returned tile may have any size and aspect
  ratio. The script **never trusts the returned pixel size**: an image
  whose aspect ratio matches the window is resized to it with Lanczos;
  anything else is rejected with the reason.
- A tile delivered smaller than the window is *genuinely lower detail*
  once resized to the window. `accept` reports the delivered size as a
  fraction of the window and warns when it is under 90% on an axis; the user
  can then re-plan with a smaller T instead of accepting soft tiles.
- A `probe` command writes a small nearest-enlarged test crop and prints
  instructions for one throwaway generation; `probe --result` records the
  delivered size and proposes T for the profile before any real tile is
  committed.

## Open Questions

- **Patch redo.** Whether a redone tile can be regenerated *without*
  discarding its dependents (see the proposal and [IDEAS](IDEAS.md)). Needs
  an experiment with a generator.

## Proposals

- **Layout and packaging:** see [Packaging](DESIGN-packaging.md).
- **Patch redo (the user's idea; not part of the first version).** To avoid
  regenerating dependents, redo a tile with the already-accepted pixels on
  *all* sides as context: the window holds the tile's area (shrunk by a
  margin) as the unknown region, with marker lines on every side that has
  accepted neighbours, and the generator is asked to fill it so that it
  matches all edges. It is the same mechanism as the seam repair tile in
  [Tiling](DESIGN-tiling.md). It only fits when the window can hold the area
  plus context on every side (a tile with a 1365 px slice leaves roughly 340 px
  a side in a 2048 px window, so a smaller area is redone at a time), and
  whether generators can fill an enclosed region reliably is unknown; it is
  to be tried on `KittensSmall.jpg` once the base workflow works.
- **Commands:** `init` (source, factor or target, profile, T, work dir; refuses a
  changed aspect ratio), `next` (prepare the next tile's input and
  instructions), `accept` (validate and merge the returned tile), `redo`,
  `probe`, `status`, `preview`, `finish` (write the final PNG).
- **Validation on `accept`:** dimensions equal the window's (if only the
  size differs and the aspect ratio is the same, resize with Lanczos and
  say so, otherwise reject); no marker-coloured line left in the new region;
  the context region correlates with the supplied context (to catch shifts
  or style changes); seams within the options of the Tiling design. Rejection
  tells the agent what to regenerate.
