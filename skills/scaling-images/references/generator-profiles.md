# Generator profiles

The scripts cannot tell which generator you have; name a profile with `init --profile`.
The figures below were researched on 2026-10-02 from public sources and change over time; treat
them as defaults and override any of them with the `custom` profile.

| Profile | Size honoured | Default tile | Use when |
| --- | --- | --- | --- |
| `gpt-image-2-api` | yes | 2048 | gpt-image-2 through the Images API, or the Codex CLI with an explicit size |
| `codex-builtin` | no | 1024 | the built-in image tool of Codex, which does not take a size |
| `custom` | your rules | 2048 | anything else; give `--multiple`, `--max-edge`, `--max-ratio`, `--min-pixels`, `--max-pixels`, `--tile` |

## gpt-image-2 rules

Each edge a multiple of 16; the long edge at most 3840 (some sources say below 3840, so 3824 is
safe); long:short at most 3:1; total pixels 655,360 to 8,294,400. About 2560x1440 is the reliable
upper bound. Windows outside these are refused by `init`; a source too small for one window needs a
larger factor.

## The built-in Codex tool

The built-in `image_gen` tool of Codex exposes no size control, and the OAuth-backed path has been
reported to ignore `size` and `quality`, returning smaller images (1024x1536 up to about 1693x929)
while reporting success. So with `codex-builtin`:

1. `init`, then `probe` to learn what size actually comes back; `probe --result FILE` recommends a tile size.
2. `accept` never trusts the returned size: a result with the right shape is resized (and warned
   about if under 90% of the window); any other shape is rejected.
3. A smaller delivered tile is genuinely softer. If warnings appear, re-plan with a smaller `--tile`
   rather than accepting soft tiles. The CLI with an explicit size and an API key is the reported
   way to get exact dimensions.
