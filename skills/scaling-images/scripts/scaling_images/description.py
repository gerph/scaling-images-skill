"""
The image description: prose for the generator and a JSON block of located content.
"""

import hashlib
import json
import re

from PIL import Image, ImageDraw


class DescriptionError(Exception):
    """The description file is missing or malformed."""


_BLOCK = re.compile(r"```json\s*\n(.*?)\n```", re.S)


def description_hash(text):
    """
    A hash that ignores line endings and trailing spaces, so trivial edits do not count.
    """
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    normalised = "\n".join(lines).strip() + "\n"
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


def load(path):
    """
    Read a description file; returns (prose, items, text).
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except IOError as exc:
        raise DescriptionError("Cannot read the description '{0}': {1}".format(path, exc))
    if not text.strip():
        raise DescriptionError("The description '{0}' is empty".format(path))

    match = _BLOCK.search(text)
    if not match:
        raise DescriptionError(
            "The description '{0}' has no fenced json block holding the content items".format(path))
    try:
        data = json.loads(match.group(1))
    except ValueError as exc:
        raise DescriptionError("The json block in '{0}' is not valid: {1}".format(path, exc))

    items = data.get("content") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise DescriptionError("The json block must be an object with a 'content' list")
    for item in items:
        box = item.get("box") if isinstance(item, dict) else None
        if "name" not in item or not isinstance(box, list) or len(box) != 4:
            raise DescriptionError("Each content item needs a name and a four-number box: {0!r}".format(item))
        x0, y0, x1, y1 = box
        if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
            raise DescriptionError("The box for '{0}' must satisfy 0 <= x0 < x1 <= 1 (and the same for y)".format(
                item["name"]))

    prose = (text[:match.start()] + text[match.end():]).strip()
    return prose, items, text


def classify(items, tile, target, accepted_mask=None):
    """
    Sort content items into those already drawn, to be drawn and outside a tile.

    Returns (in_context, new, outside); each entry is (item, continues) where
    *continues* is True when a new item is already partly drawn in the context.
    """
    tw, th = target
    ax0, ay0, ax1, ay1 = tile["acc"]
    wx0, wy0, wx1, wy1 = tile["win"]
    in_context, new, outside = [], [], []

    for item in items:
        bx0, by0, bx1, by1 = item["box"]
        x0, y0 = int(bx0 * tw), int(by0 * th)
        x1, y1 = max(x0 + 1, int(round(bx1 * tw))), max(y0 + 1, int(round(by1 * th)))

        touches_new = x0 < ax1 and ax0 < x1 and y0 < ay1 and ay0 < y1
        drawn = False
        if accepted_mask is not None:
            cx0, cy0, cx1, cy1 = max(x0, wx0), max(y0, wy0), min(x1, wx1), min(y1, wy1)
            if cx0 < cx1 and cy0 < cy1:
                drawn = bool(accepted_mask[cy0:cy1, cx0:cx1].any())

        if touches_new:
            new.append((item, drawn))
        elif drawn:
            in_context.append((item, False))
        else:
            outside.append((item, False))
    return in_context, new, outside


def overlay(source, items):
    """
    The original with each content item's box outlined and named, for review.
    """
    image = source.convert("RGB")
    draw = ImageDraw.Draw(image)
    w, h = image.size
    for item in items:
        x0, y0, x1, y1 = item["box"]
        rect = (x0 * w, y0 * h, x1 * w - 1, y1 * h - 1)
        draw.rectangle(rect, outline=(255, 255, 0), width=max(1, w // 400))
        draw.text((rect[0] + 3, rect[1] + 2), item["name"], fill=(255, 255, 0))
    return image
