"""
The written instructions an agent follows to have a generator redraw one tile.

Agent-neutral: no tool names, only what the image is, what to draw and where to save it.
"""

from .state import tile_label


def _colour_name(rgb):
    names = {(255, 255, 255): "white", (0, 0, 0): "black", (128, 128, 128): "grey"}
    return names.get(tuple(rgb), "#{0:02x}{1:02x}{2:02x}".format(*rgb))


def _percent(value, total):
    return int(round(100.0 * value / total))


def _items(title, entries, continues_note=False):
    if not entries:
        return []
    lines = [title]
    for item, continues in entries:
        note = " ({0})".format(item["note"]) if item.get("note") else ""
        extra = " - already partly drawn in the context; continue it, do not repeat it" if (
            continues and continues_note) else ""
        lines.append("  - {0}{1}{2}".format(item["name"], note, extra))
    return lines


def build(state, tile, prose, groups, paths, colour_name):
    """
    The instruction text for *tile*.

    *groups* is (in_context, new, outside) from description.classify; *paths* has
    'input', 'original', 'locator' and 'result'.
    """
    target = state["target"]
    width, height = tile["size"]
    total = len(state["tiles"])
    first = not tile["marker_left"] and not tile["marker_top"]
    wx0, wy0, wx1, wy1 = tile["win"]
    ax0, ay0, ax1, ay1 = tile["acc"]
    marker = state["marker"]["width"]

    lines = []
    lines.append("TILE {0} ({1} of {2}) of a {3}x{4} enlargement".format(
        tile_label(tile), tile["index"] + 1, total, target[0], target[1]))
    lines.append("")
    lines.append("Task: redraw the image at '{0}' at higher quality and save the result to '{1}'.".format(
        paths["input"], paths["result"]))
    lines.append("The result must be a PNG of exactly {0}x{1} pixels with the same framing as the input.".format(
        width, height))
    if not state["profile"].get("honours_size", True):
        lines.append("If your tool cannot be given a size, any size with the same shape is acceptable; "
                     "it will be resized (and will be softer if it is smaller than {0}x{1}).".format(width, height))
    lines.append("")

    restyle = state["options"].get("restyle", False)
    if first and restyle:
        lines.append("The input is the top-left part of the original, enlarged with blocky nearest-neighbour "
                     "pixels. Repaint all of it in the TARGET STYLE given in the description below. Keep the "
                     "subject, the layout, the position and proportions of every shape, and the identity of every "
                     "colour (a red object stays red). Do not copy how the original is rendered (its outlines, flat "
                     "fills, cartoon shading or other technique); the 'original style' notes describe the source "
                     "only. Do not add, remove or move anything.")
    elif first:
        lines.append("The input is the top-left part of the original, enlarged with blocky nearest-neighbour "
                     "pixels. Redraw all of it with full detail, keeping every shape, line, colour and the "
                     "layout of the input. Do not add, remove or move anything.")
    else:
        lines.append("Part of the input is finished artwork; the rest is a blocky nearest-neighbour enlargement "
                     "of the original that you must redraw with full detail.")
        if tile["marker_left"]:
            lines.append("- A solid {0} vertical line {1} pixels wide marks the left edge of the part to redraw. "
                         "Everything to the LEFT of that line is finished: keep it identical in position, "
                         "content and colour. Redraw the {0} line and everything to its right, continuing the "
                         "finished artwork across the line without any visible join.".format(colour_name, marker))
        if tile["marker_top"]:
            lines.append("- A solid {0} horizontal line {1} pixels tall marks the top edge of the part to redraw. "
                         "Everything ABOVE that line is finished: keep it identical. Redraw the {0} line and "
                         "everything below it, continuing the finished artwork across the line without any "
                         "visible join.".format(colour_name, marker))
        lines.append("- The marker lines are not part of the picture; none may remain in the result.")
    if restyle:
        lines.append("- Match the target style, brushwork, texture and colour treatment of the finished artwork "
                     "exactly, and keep the palette of the original.")
    else:
        lines.append("- Match the style, texture, detail level and colour of the finished artwork exactly. Keep the "
                     "colour grade (tint, saturation, contrast, brightness and any gradient across the sky or "
                     "ground) of the finished artwork and of the original; do not make it more vivid, sharper or "
                     "more dramatic.")
    if state.get("alpha", {}).get("mode"):
        lines.append("- The background is a plain {0} backdrop standing in for transparency. Keep it perfectly "
                     "flat and plain: no texture, shadow, vignette or canvas grain. It is not part of the "
                     "artwork.".format(_colour_name(state["alpha"]["background"])))
    lines.append("- Do not invent objects that the original does not contain.")
    lines.append("- Keep the exact framing of the input. Do not add a border, frame, margin or vignette unless the "
                 "input already shows one.")
    lines.append("- Do not draw any object, label or feature that lies outside this tile. If something is cut off at "
                 "the edge of the input it stays cut off, and nothing beyond the edge is added.")
    if restyle:
        lines.append("- Where the input looks flat or blocky it is only a low-resolution enlargement: paint it in "
                     "the target style, with the texture and detail that style has.")
    else:
        lines.append("- Where the input looks flat or blocky it is only a low-resolution enlargement: redraw the "
                     "natural texture and fine detail of the medium there (fields, water, stone, sky grain, paper) "
                     "as in the finished artwork, and do not turn it into smooth colour.")
    if tile["pad"][0] or tile["pad"][1]:
        lines.append("- The last {0} columns and {1} rows repeat the image edge to reach the required size; "
                     "continue the image naturally there (they are cropped afterwards).".format(*tile["pad"]))
    if ax1 - ax0 < wx1 - wx0 and not tile["marker_left"]:
        lines.append("- Only the left {0} pixels will be kept, but redraw the whole image.".format(ax1 - ax0))
    lines.append("")

    lines.append("Where this is in the original: columns {0}% to {1}% across and rows {2}% to {3}% down.".format(
        _percent(wx0, target[0]), _percent(wx1, target[0]), _percent(wy0, target[1]), _percent(wy1, target[1])))
    lines.append("")
    lines.append("Reference images (only if your tool accepts several inputs; use them to understand the whole "
                 "picture, never copy them into the result):")
    lines.append("  - '{0}': the whole original, unenlarged".format(paths["original"]))
    lines.append("  - '{0}': the original with this tile's footprint outlined".format(paths["locator"]))
    lines.append("")

    in_context, new, outside = groups
    lines.extend(_items("Already drawn in the finished artwork (keep, do not repeat or move):", in_context))
    lines.extend(_items("To be drawn in the redrawn area:", new, continues_note=True))
    lines.extend(_items("Not in this tile (do not draw):", outside))
    if in_context or new or outside:
        lines.append("")

    lines.append("Style and composition of the whole picture (apply throughout):")
    lines.append("")
    lines.append(prose)
    lines.append("")
    lines.append("When the result is saved, run: scale_image.py accept --work {0}".format(paths["work"]))
    lines.append("(it validates the tile and merges it; then run 'next' for the following tile).")
    return "\n".join(lines) + "\n"
