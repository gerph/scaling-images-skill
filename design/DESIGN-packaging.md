# Packaging

Part of [Image scaling skill](OVERVIEW.md). Packages the behaviour in
[Workflow](DESIGN-workflow.md), [Tiling](DESIGN-tiling.md) and
[Description](DESIGN-description.md).

## Decisions

- The finished skill will be distributed as one skill in a repository of
  agent skills that builds skills for release and lets users install them,
  in the style of [gerph/riscos-agent-skills](https://github.com/gerph/riscos-agent-skills)
  (not that repository). Checked on 2026-10-02 against its public README
  summary only: skills sit under `skills/<name>/` with a `SKILL.md`, names
  are lower-case and hyphenated, and the repository ships plug-in
  configurations for Claude, Codex, Gemini CLI and Qwen Code. I have not
  seen its release build, so how it packages scripts is unverified.
- Because the skill will be used by several agents, `SKILL.md` and the
  script messages are written in agent-neutral terms (no tool names from a
  single agent), and the scripts are plain Python invoked by path relative to
  the skill's directory.
- Licence: MIT. Authorship in the scripts' headers is Charles Ferguson
  (Gerph).

- **Dependencies are installed for the user, with no friction.** The scripts
  need Pillow (and numpy for the seam measures). The entry point checks for
  them at start. If they are missing it prints the exact install command
  and stops. A `setup` subcommand does the install itself, either into the
  current Python or, with `--venv <dir>`, into a virtual environment it
  creates. Agreed by the user ("remove any friction").
- **Packaging is tested**, and so is the logic without any generator, so the
  skill can be exercised without spending generator tokens (see Tests).

## Open Questions

- How the destination repository's release build treats `scripts/` and any
  `requirements.txt` (unverified); the install story above does not depend on
  it.

## Proposals

- **Skill name and layout**, so that the directory can be copied into the
  destination repository unchanged:

      skills/scaling-images/
          SKILL.md            the workflow for the agent, kept short
          scripts/            the Python scripts (one entry point, subcommands)
          references/         the description format, generator profiles,
                              seam treatments (loaded on demand)
      design/                 this design (not shipped in the skill)
      tests/                  tests (not shipped in the skill)

  When writing the skill itself, the repository's own skill-writing guidance
  (the `updating-robe-skills` skill) must be read first.
- **Venv handling** (the detail of the decision above). `setup --venv <dir>`
  runs `python -m venv`, installs from `requirements.txt` (minimum versions,
  not pinned tightly) and records the venv's location in a small file in the
  work directory (and honours an environment variable); from then on the entry
  point re-runs itself under that venv's Python, so the agent keeps calling
  the same command. `setup --check` reports what is present. Where the
  system Python refuses a global install (the "externally managed
  environment" case on many Linux distributions) the message recommends
  `setup --venv` rather than a way of forcing the install.
- **Tests (run without any generator):**
  - geometry tests on synthetic images: slice sizes (including the worked
    examples in [Tiling](DESIGN-tiling.md)), window rounding to multiples of
    16, context and marker placement, and the never-a-sliver rule;
  - a *fake generator* that takes a tile's input and returns it with
    controlled defects (shifted, tone-shifted, wrong size, marker left
    behind) to prove `accept` accepts or rejects each correctly;
  - an end-to-end run on `KittensSmall.jpg` with the fake generator,
    checking the final PNG has the target size and the seams report;
  - resume tests (stop part-way, then continue) and the description-change
    pause;
  - **package tests**: copy only the files the release would ship into a
    clean temporary directory, check that `SKILL.md` has a valid header (its
    name matches the directory, it has a description) and links nothing that is
    not shipped, run `setup --venv` there, and run a tiny end-to-end job with
    the fake generator from that copy.
- **Changelog and release notes:** a `CHANGELOG.md`, kept per the
  repository's usual practice, with a version number that rises with
  significant features.
