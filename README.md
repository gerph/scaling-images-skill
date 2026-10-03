# Scaling images

An agent skill that enlarges an image far beyond what an image generator can draw in one go, while keeping its style
consistent and its joins invisible.

Asking a generator to draw a large image "in tiles" usually goes badly: neighbouring tiles disagree at their edges and
the style drifts. This skill builds the large image one tile at a time instead. Each tile is redrawn by the generator
with the already finished high-resolution pixels beside it, a rough enlargement of the part not yet drawn, a marker line
showing where to start, and a written description that restates the style and the content every time. Python scripts do
the geometry, compositing, checking and bookkeeping; the agent describes the image and drives the generator; you review
the description and look at the results.

It has been tried with Codex's built-in image tool on a photograph, a relief map full of lettering, and a cartoon
restyled as oil paint, with a transparent background kept.

## What you need

- An AI agent that can run shell commands, read and show images, and call an image generator.
- Python 3.9 or later with Pillow and numpy (the skill can install them for you, see below).
- An image generator. The scripts never call one; the agent uses whichever tool it has.

## Installing

The skill is the directory `skills/scaling-images/` (it contains `SKILL.md`). Install it the way your agent installs any
skill. For Claude Code that is a copy in `~/.claude/skills/` (or `.claude/skills/` in a project); other agents have their
own place, so check their documentation. Each release also provides `scaling-images.skill`, a zip of that directory.

Then install the Python packages. The agent will do this if they are missing, or you can:

    python3 skills/scaling-images/scripts/scale_image.py setup               # into this Python
    python3 skills/scaling-images/scripts/scale_image.py setup --venv ~/.scaling-images-venv

`setup --venv` creates a virtual environment, installs into it and remembers it, so later runs use it automatically
(useful where the system Python refuses a global install). `setup --check` shows what is present.

## Using it

Ask your agent, naming the skill, the image and what you want. For example:

> Use skills/scaling-images to scale Gems.png to 5x in a new work directory called Gems-5x-b. Render it in heavy oil
> brushstrokes. The source has a transparent background: keep the alpha, on a white backdrop. It is a hard-edged cartoon,
> so use `--enlarge smooth`.

You can give a factor (`5x`) or a target size (`3840x2160`). The aspect ratio must stay the same: padding and cropping
are not supported yet.

The agent then works through these steps. The ones marked **you** need a decision from you.

1. **Describes the image.** It looks at the original at full size and writes `description.md`: the medium, technique,
   style, focus, light and colour grade, typography, what the file format added that is not artwork (such as JPEG blocks),
   and the content (each important feature with a rough position, plus any text with its exact wording).
2. **You review the description.** Change anything: this text goes to the generator with every tile, so it is where
   you steer the result. Nothing is generated until you approve it.
3. **You make a few choices**, which the agent should ask about:
   - *Restyle?* To render in a different style, the description gets a "Target style" section and the run uses `--restyle`.
   - *Transparency?* If the source has transparent areas, either composite onto a colour (white by default) for an
     opaque result, or keep the alpha: the picture is generated on a plain backdrop and the original alpha is restored,
     scaled up, for an RGBA PNG.
   - *Hard-edged art?* For cartoons, icons and line art, `--enlarge smooth` stops the generator copying the staircase
     edges of a blocky enlargement.
4. **Plans the tiles** (`init`). It tells you how many there are, and refuses requests that break the generator's size
   rules.
5. **Learns what size the generator really delivers** (`probe`), for tools that ignore the requested size.
6. **Draws each tile in turn** (`next`, generate, `check`, `accept`). The agent looks at each result and at 1:1 crops of
   the new seams, regenerates when something is wrong, and tells you about warnings.
7. **Finishes** (`finish`): writes the final PNG at exactly the target size, with a preview.

Each tile is a separate generation, one after another, so a large job takes a while and uses that many generations.
Examples from real runs with Codex's built-in tool (1248-pixel tiles): a 640x480 photograph at 3x took four tiles, a
1536x1024 map at 2x took eight, and a 320x320 cartoon at 5x took four.

If you change the description part-way through, every command stops ("paused") and the agent asks you what to do:
revert it, adopt the change from the current tile on, or redo from a tile. It never chooses for you.

## Getting good results

- **Write the colour grade into the description.** Generators drift: warmer, more vivid, more contrasty. State the tint,
  saturation, contrast and any gradient across the sky, and say what must not change.
- **Give positions for the important content** so each tile is told what is already drawn, what to draw and what is not in it.
- **Look at the seam crops.** The seam numbers are a guide; your eyes are the check. A tile is cheapest to redo before the
  next one is made.
- **Textures made of repeating marks** (stitches, tiles, weave) blend badly across a 128-pixel feather, as two layouts
  average into a muddy band. Try a narrower `--feather`.
- **Lettering**: check every label in every tile. Small text is where generators fail first.
- **Restyling** turns the layout check off, since a new style changes the edges.

## The commands

All are run as `python3 skills/scaling-images/scripts/scale_image.py COMMAND ...`, and (except `init` and `setup`) take
`--work DIR`, the work directory given to `init`, or run from inside it. Everything needed to resume is in that
directory, so a run can continue in a later session.

| Command | What it does |
| --- | --- |
| `setup [--venv DIR] [--check]` | Install or check the Python packages. |
| `init SOURCE --factor N` (or `--target WxH`) | Plan the tiles and start a run. |
| `probe [--result FILE]` | Learn the size a generator really delivers and recommend a tile size. |
| `next` | Write the next tile's input image and print its instructions. |
| `check [FILE]` | Run every validation on a candidate result without merging it. |
| `accept [FILE]` | Validate and merge the result, then measure the seams. |
| `redo TILE [--yes]` | Discard a tile and the later tiles that used its pixels (it asks first). |
| `status`, `preview` | Show progress; write a downscaled preview and the seam report. |
| `finish [--output FILE]` | Write the final PNG. |
| `description [--adopt] [--redo-from TILE --yes]` | Check, or adopt, an edited description. |

Exit status: 0 done, 1 error, 2 tile rejected, 3 paused (description changed), 4 needs your confirmation (`redo`),
5 accepted with warnings.

Main `init` options:

| Option | Meaning |
| --- | --- |
| `--profile` | `gpt-image-2-api` (the size you ask for is honoured), `codex-builtin` (it is not), or `custom` with `--multiple`, `--max-edge`, `--max-ratio`, `--min-pixels`, `--max-pixels`. |
| `--tile N` | Tile size; defaults to 2048, or 1248 for `codex-builtin`. |
| `--context N` | Pixels of finished artwork shown beside each new tile (default a third of the tile). |
| `--feather N` | Cross-fade width at each seam (default 128; 0 for a hard cut). |
| `--anchor auto\|on\|off` | Pull each tile's broad colour back to the original's, so errors cannot add up across a large image (auto: on unless `--restyle`). |
| `--enlarge nearest\|smooth` | How the not-yet-drawn part of each input is enlarged. |
| `--restyle` | Render in the Target style given in the description. |
| `--alpha composite\|keep`, `--background` | What to do with transparency, and the backdrop colour (default white). |
| `--no-structure`, `--no-tone`, `--no-align` | Turn off the layout check, colour correction or alignment. |
| `--marker-width N` | Marker line width (default 6). |

## What it checks

On every tile it checks the returned size and shape (resizing a tile of the right shape, and warning if it is much smaller
than asked), that the marker line has gone, and that the generator's copy of the finished artwork still matches ours. It
corrects a small shift, and colour drift from top to bottom or left to right, then cross-fades each seam into the
generator's copy of the context. It reports how visible each seam is, and warns when the tile's layout has drifted from
the original (for example an edge that has moved). See `skills/scaling-images/references/` for the details.

## Limits

- The aspect ratio cannot change yet (no padding or outpainting).
- Tiles are drawn one after another.
- A generator may still change colour, add or lose small detail, or draw text wrongly; the checks warn, they do not
  guarantee.
- Sizes and limits of generators change; the figures in the profiles come from public sources checked at the time.

## Development

    pip install -r requirements-dev.txt
    pytest tests/                 # a few minutes; a fake generator is used, so no network or tokens
    python3 check-skills.py       # validates the skill's SKILL.md, metadata and links

The continuous integration (`.github/workflows/ci.yml`) runs the skill check and the tests on Python 3.9 and 3.12, builds
`scaling-images.skill`, and drafts a release for tags beginning `v` (the tag must match the version the scripts report).
`check-skills.py` is the checker from the agent-skills repository this skill is distributed through.

The design, the implementation plan and the trial results are in `design/` (start with `design/OVERVIEW.md`). The
version is in `skills/scaling-images/scripts/scaling_images/__init__.py` and `CHANGELOG.md`.

## Licence

MIT. Author: Charles Ferguson (Gerph).
