# Ideas

Loosely given thoughts to challenge and expand before they become designs.
An idea is removed from this file once a design captures it. See the
Rejected section for ideas we have decided against, and why.

## Aspect-ratio expansion (outpainting)

Status: open
Kind: idea
Waiting on: the base tiling workflow working on KittensSmall.jpg

Generate new content to change the aspect ratio (for example 4:3 to 16:9),
keeping the style and the content of the artwork. This also covers padding
when a target resolution has a different aspect ratio to the source. It
would extend the description (to say what the new areas should contain) and
reuse the tiling mechanism, with the new areas being unknown regions that
have no source image behind them. For now the skill requires matching
aspect ratios.

## Progressive enlargement

Status: open
Kind: idea
Waiting on: the base tiling workflow, and a look at how a single large factor
behaves

For large factors, enlarge in successive passes (for example 2x each time)
so each pass's crude input carries more information. Concern from the user:
repeated passes may only magnify and smooth repeating detail such as waves,
rather than redrawing it smaller and more accurately. The description's
"detail scale" element (see [Description](DESIGN-description.md)) is meant to
address this in every pass; whether that is enough is for experiment. In the
meantime a user can chain runs by hand (the output of one is the source of
the next).

## Direct image API back end

Status: open
Kind: idea
Waiting on: the agent-driven workflow working with at least one generator

Let the scripts optionally call an image API themselves (for example the
OpenAI Images API with an API key from the environment) so that sizes are
deterministic, instead of the agent calling a generator tool. The user wants
the skill to work with any generator rather than one system, so this is an
optional extra behind the same `accept` step and not the main path. Not yet
checked: how the edit endpoint takes several input images; credentials must
never be written to the state file; cost per tile should be shown first.

## Patch redo (regenerating a tile with all neighbours as context)

Status: open
Kind: idea
Waiting on: the base workflow, and an experiment to see whether a generator
can fill an enclosed marked region

When a tile is bad, redo it with the accepted pixels on every side shown as
context, and the tile's area (shrunk by a margin) marked with red lines on
each side that has neighbours, asking the generator to match all of them.
This could save regenerating the later tiles that used the bad tile as
context. It is the same mechanism as the seam repair tile. Limits: the window
must hold the area plus context all round, and it asks the generator to match
two sides at once, which may fail where matching one side works. See
[Workflow](DESIGN-workflow.md).

## Rejected
