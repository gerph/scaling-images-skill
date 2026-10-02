# Plan: Workflow

Part of the [implementation plan](OVERVIEW.md#implementation-plan). Implements
[DESIGN-workflow.md](DESIGN-workflow.md).

## Dependencies

- Depends on: [PLAN-tiling.md](PLAN-tiling.md) Stages 1 to 3 and
  [PLAN-description.md](PLAN-description.md) Stages 1 and 2.
- Blocks: [PLAN-packaging.md](PLAN-packaging.md) Stages 2 to 5.
- Independent of: nothing useful; its stages build on each other.

## Stages

### Stage 1 — Fake generator, state and `init`

- [ ] `tests/fake_generator.py`: given a tile input and options, returns a
      plausible "generated" tile: the ideal image for the window with optional
      defects (shift, tone shift, wrong size, wrong aspect ratio, marker left
      behind, lower resolution). Built first so every later stage tests without
      spending tokens.
- [ ] `state.py`: JSON state file (parameters, grid, accepted tiles with the
      description hash, current tile, description-version history). Atomic
      write (write then rename).
- [ ] `profiles.py`: `gpt-image-2-api`, `codex-builtin`, `custom`.
- [ ] `scale_image.py init`: source, `--factor` or `--target`, `--profile`,
      `--tile`, `--work`, description path. Refuses a changed aspect ratio and
      windows outside the profile. Default work directory `<source-stem>-scaling/`
      next to the source.

**Acceptance:** `pytest tests/test_init.py`: `init` on `KittensSmall.jpg --factor 4`
writes a state file whose grid has two tiles with the worked-example sizes;
`--target 2560x1440` fails with the aspect-ratio message; a state file survives
a re-read unchanged.

### Stage 2 — `next` (instructions)

- [ ] Writes the tile input, original and locator images, and prints the
      instructions: what to redraw, the marker meaning, the output path and the
      wanted size, the style prose, and the three content groups.
- [ ] Output is agent-neutral (no tool names); also written to a text file so
      it can be re-read.

**Acceptance:** `pytest tests/test_next.py`: for the kittens job, tile 0
instructions say to redraw the whole tile and tile 1 mention the red line and
the context; content items are listed in the right group; instructions are
stable across a re-run.

**Notes:** The instructions must say plainly what the generator must *not* do:
invent objects in the unknown region that the content list does not give, move
or restyle the context, or keep the marker line.

### Stage 3 — `accept` (validation and merge)

- [ ] Dimension check and Lanczos resize for a matching aspect ratio, reject
      otherwise; warning below 90% of the window.
- [ ] Residual-marker check; context correlation check.
- [ ] Applies the Tiling merge and the seam options; writes seam crops.
- [ ] Exit statuses distinguish accepted, accepted with warnings and rejected.

**Acceptance:** `pytest tests/test_accept.py` with the fake generator: ideal
tile accepted; wrong size with a matching aspect ratio resized and warned;
wrong aspect ratio rejected; marker left behind rejected; shifted tile
corrected; strongly different context rejected.

### Stage 4 — Description-change pause and `description --adopt`

- [ ] Hash comparison at the start of every command except `status` and `preview`
      (distinct exit status; message gives the three choices).
- [ ] `description --adopt`, recorded in the version history.

**Acceptance:** `pytest tests/test_description_change.py`: edit between `next`
and `accept` pauses and changes nothing; `--adopt` continues and records the
version; a whitespace edit does not pause.

### Stage 5 — `redo`, `status`, `preview`, `finish`

- [ ] `redo` (lists dependents, confirms, keeps old pixels until accepted).
- [ ] `status`, `preview` (downscaled canvas, tile and seam overlay, seam
      report), `finish` (final PNG at the exact target size).
- [ ] Keep rule: `next` marks the previous tile kept.

**Acceptance:** `pytest tests/test_redo.py tests/test_finish.py`: redoing tile 0 of
a 3x3 job lists the right dependents; an interrupted run resumes; the finished
PNG is the target size and equals the fake generator's ideal image.

### Stage 6 — `probe`

- [ ] Writes a small nearest-enlarged test crop and instructions;
      `probe --result` records the delivered size and prints a recommended
      tile size.

**Acceptance:** `pytest tests/test_probe.py` with the fake generator
delivering 1672x941: the recommendation fits the profile rules.

## Later (optional/deferred)

- Patch redo; direct API back end (both in [IDEAS](IDEAS.md)).

## Open Questions

- The confirm step in `redo` is interactive; whether an agent run needs a
  `--yes` flag (proposed: yes, to be passed only after the user agrees).
