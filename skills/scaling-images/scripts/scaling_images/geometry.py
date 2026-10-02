"""
Geometry: target size, slice planning and the tile grid.

Pure integer arithmetic with no image dependencies, so it can be tested alone.
Rectangles are (x0, y0, x1, y1) with x1 and y1 exclusive.
"""

import math


class GeometryError(Exception):
    """A requested scale, tile size or window cannot be met."""


class AspectRatioError(GeometryError):
    """The target aspect ratio differs from the source's."""


def _round_up(value, multiple):
    return ((value + multiple - 1) // multiple) * multiple


def _round_down(value, multiple):
    return (value // multiple) * multiple


def target_size(source, factor=None, target=None):
    """
    Work out the exact target size from a factor or a target resolution.

    A target whose aspect ratio differs from the source's (beyond rounding)
    raises AspectRatioError; padding and cropping are not supported yet.
    """
    sw, sh = source
    if (factor is None) == (target is None):
        raise GeometryError("Give either a factor or a target size, not both or neither")

    if factor is not None:
        if factor <= 0:
            raise GeometryError("The factor must be positive")
        return (max(1, int(math.floor(sw * factor + 0.5))), max(1, int(math.floor(sh * factor + 0.5))))

    tw, th = target
    if tw <= 0 or th <= 0:
        raise GeometryError("The target size must be positive")
    if abs(th - sh * tw / float(sw)) > 1.0 and abs(tw - sw * th / float(sh)) > 1.0:
        raise AspectRatioError(
            "The target {0}x{1} has a different aspect ratio to the source {2}x{3}; "
            "padding or cropping is not supported yet".format(tw, th, sw, sh))
    return (tw, th)


def _equal_slices(length, count):
    base, extra = divmod(length, count)
    return [base + (1 if i < extra else 0) for i in range(count)]


def plan_axis(length, tile, context, min_slice):
    """
    Split an axis of *length* pixels into the slices a series of tiles will own.

    The first slice takes a full tile when that leaves a proportionate
    remainder; otherwise every slice is made equal. Later slices never exceed
    tile - context, so each has at least *context* pixels of accepted pixels
    beside it, and none is below *min_slice*.
    """
    if length <= tile:
        return [length]

    cap = tile - context
    if cap <= 0:
        raise GeometryError("The context must be smaller than the tile")

    count = 1 + int(math.ceil((length - tile) / float(cap)))
    candidates = []

    # Preferred: a full first slice, the rest equal.
    rest = _equal_slices(length - tile, count - 1)
    candidates.append([tile] + rest)
    # Fallback: everything equal.
    candidates.append(_equal_slices(length, count))
    # Last resort: one more slice, equal.
    candidates.append(_equal_slices(length, count + 1))

    for slices in candidates:
        if min(slices) >= min_slice and max(slices[1:]) <= cap and slices[0] <= tile:
            # Reject a remainder that is disproportionately smaller (under half of cap).
            if slices[0] == tile and len(slices) > 1 and min(slices[1:]) * 2 < cap:
                continue
            return slices
    raise GeometryError(
        "Cannot split {0} pixels into slices of at least {1} within tile {2} and context {3}".format(
            length, min_slice, tile, context))


def _axis_windows(slices, length, tile, multiple):
    """
    For each slice, the accepted span and the window span along one axis.

    Returns a list of dicts: acc0, acc1, win0, win1 (real pixels), pad (extra
    edge-repeated pixels beyond *length*) and size (win1 - win0 + pad).
    """
    result = []
    start = 0
    for index, size in enumerate(slices):
        acc0, acc1 = start, start + size
        start = acc1

        if index == 0:
            w0, w1 = 0, min(tile, length)
        else:
            w1 = acc1
            w0 = max(0, acc1 - tile)

        # Grow to a multiple, towards the accepted side, then outwards, then pad.
        wanted = _round_up(w1 - w0, multiple)
        extra = wanted - (w1 - w0)
        if extra and index > 0 and w0 > 0:
            take = min(extra, w0)
            w0 -= take
            extra -= take
        if extra:
            take = min(extra, length - w1)
            w1 += take
            extra -= take
        pad = extra
        result.append({"acc0": acc0, "acc1": acc1, "win0": w0, "win1": w1,
                       "pad": pad, "size": w1 - w0 + pad})
    return result


def plan_grid(target, profile, tile=None, context=None, min_slice=None):
    """
    Plan every tile for a target size, in row-major order.

    Each tile is a dict with its row/col, accepted rectangle ("acc"), window
    rectangle ("win", real pixels), "pad" (right, bottom), "size" (the window
    size as generated, including padding) and which marker lines apply.
    """
    tile = tile or profile.tile
    multiple = profile.multiple
    tile = _round_down(tile, multiple)
    if tile <= 0:
        raise GeometryError("The tile size is below the generator's multiple")
    context = context if context is not None else _round_down(int(round(tile / 3.0)), 1)
    min_slice = min_slice if min_slice is not None else tile // 4
    min_context = tile // 8
    if context < min_context:
        raise GeometryError("The context {0} is below the minimum {1}".format(context, min_context))

    width, height = target
    cols = _axis_windows(plan_axis(width, tile, context, min_slice), width, tile, multiple)
    rows = _axis_windows(plan_axis(height, tile, context, min_slice), height, tile, multiple)

    tiles = []
    for r, row in enumerate(rows):
        for c, col in enumerate(cols):
            entry = {
                "index": len(tiles),
                "row": r,
                "col": c,
                "acc": [col["acc0"], row["acc0"], col["acc1"], row["acc1"]],
                "win": [col["win0"], row["win0"], col["win1"], row["win1"]],
                "pad": [col["pad"], row["pad"]],
                "size": [col["size"], row["size"]],
                "marker_left": c > 0,
                "marker_top": r > 0,
            }
            profile.check_window(entry["size"][0], entry["size"][1])
            tiles.append(entry)
    return tiles


def rects_overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def dependents(tiles, index):
    """
    Indices of later tiles that used pixels from tile *index* (transitively).

    A later tile depends on an earlier one when its window overlaps the earlier
    tile's accepted rectangle.
    """
    affected = [tiles[index]]
    found = []
    for later in tiles[index + 1:]:
        if any(rects_overlap(later["win"], earlier["acc"]) for earlier in affected):
            affected.append(later)
            found.append(later["index"])
    return found
