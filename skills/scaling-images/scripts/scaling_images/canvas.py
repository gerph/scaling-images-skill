"""
The canvas of accepted pixels, tile input rendering and merging.
"""

import os

import numpy as np
from PIL import Image

MARKER_CANDIDATES = [
    ("red", (255, 0, 0)),
    ("magenta", (255, 0, 255)),
    ("green", (0, 255, 0)),
    ("cyan", (0, 255, 255)),
    ("yellow", (255, 255, 0)),
]


def choose_marker_colour(source):
    """
    Pick the candidate colour least present in *source*; returns (name, (r, g, b)).
    """
    small = source.convert("RGB")
    small.thumbnail((256, 256))
    pixels = np.asarray(small, dtype=np.int32).reshape(-1, 3)
    best = None
    for name, colour in MARKER_CANDIDATES:
        distance = np.sqrt(((pixels - np.array(colour)) ** 2).sum(axis=1))
        share = float((distance < 90).mean())
        if best is None or share < best[0]:
            best = (share, name, colour)
    return best[1], best[2]


class Canvas(object):
    """
    Accepted high-resolution pixels (RGB) with a mask of which are accepted.
    """

    def __init__(self, size):
        self.size = tuple(size)
        self.pixels = np.zeros((size[1], size[0], 3), dtype=np.uint8)
        self.mask = np.zeros((size[1], size[0]), dtype=bool)

    @classmethod
    def load(cls, work):
        image = Image.open(os.path.join(work, "canvas.png")).convert("RGB")
        mask = Image.open(os.path.join(work, "mask.png")).convert("L")
        canvas = cls(image.size)
        canvas.pixels = np.array(image)
        canvas.mask = np.array(mask) > 0
        return canvas

    def save(self, work):
        # Write then rename so an interrupted save cannot leave a torn file.
        for name, array in (("canvas.png", self.pixels), ("mask.png", self.mask.astype(np.uint8) * 255)):
            path = os.path.join(work, name)
            temp = path + ".tmp.png"
            Image.fromarray(array).save(temp)
            os.replace(temp, path)

    def window_mask(self, tile):
        """
        The accepted mask for a tile's window (padding counts as not accepted).
        """
        x0, y0, x1, y1 = tile["win"]
        out = np.zeros((tile["size"][1], tile["size"][0]), dtype=bool)
        out[:y1 - y0, :x1 - x0] = self.mask[y0:y1, x0:x1]
        return out


def nearest_region(source_array, target, rect):
    """
    The part of the nearest-neighbour enlargement of the source covering *rect*.

    Source pixels are chosen by pixel centre so a non-integer scale does not
    shift content across a seam.
    """
    sh, sw = source_array.shape[:2]
    tw, th = target
    x0, y0, x1, y1 = rect
    xs = np.minimum(((np.arange(x0, x1) + 0.5) * sw / float(tw)).astype(np.int64), sw - 1)
    ys = np.minimum(((np.arange(y0, y1) + 0.5) * sh / float(th)).astype(np.int64), sh - 1)
    return source_array[ys][:, xs]


def unknown_origin(tile):
    """
    Where the unknown region starts in window coordinates: (ux, uy).
    """
    return (tile["acc"][0] - tile["win"][0] if tile["marker_left"] else 0,
            tile["acc"][1] - tile["win"][1] if tile["marker_top"] else 0)


def draw_markers(array, tile, colour, width):
    """
    Draw the marker lines (in place) over the first pixels of the unknown region.
    """
    ux, uy = unknown_origin(tile)
    if tile["marker_left"]:
        array[uy:, ux:ux + width] = colour
    if tile["marker_top"]:
        array[uy:uy + width, ux:] = colour
    return array


def render_input(source, canvas, tile, colour, width):
    """
    The image to give a generator for a tile, as a PIL image of the window size.

    Accepted pixels come from the canvas; the rest is the original enlarged with
    nearest-neighbour. Padding repeats the edge. Marker lines are drawn last.
    """
    source_array = np.asarray(source.convert("RGB"))
    x0, y0, x1, y1 = tile["win"]
    window = nearest_region(source_array, canvas.size, tile["win"]).copy()
    accepted = canvas.mask[y0:y1, x0:x1]
    window[accepted] = canvas.pixels[y0:y1, x0:x1][accepted]

    pad_x, pad_y = tile["pad"]
    if pad_x or pad_y:
        window = np.pad(window, ((0, pad_y), (0, pad_x), (0, 0)), mode="edge")

    draw_markers(window, tile, colour, width)
    return Image.fromarray(window)


def merge(canvas, tile, generated):
    """
    Copy the new region of a generated window (a numpy array) into the canvas.

    Only the accepted rectangle is taken; the generator's copy of the context
    is discarded.
    """
    ax0, ay0, ax1, ay1 = tile["acc"]
    wx0, wy0 = tile["win"][0], tile["win"][1]
    canvas.pixels[ay0:ay1, ax0:ax1] = generated[ay0 - wy0:ay1 - wy0, ax0 - wx0:ax1 - wx0]
    canvas.mask[ay0:ay1, ax0:ax1] = True


def feather_width(tile, width):
    """
    The feather band widths (left, top) available to a tile: no wider than the context beside the seam.
    """
    ux, uy = unknown_origin(tile)
    return (min(width, ux, tile["acc"][0]) if tile["marker_left"] else 0,
            min(width, uy, tile["acc"][1]) if tile["marker_top"] else 0)


def apply_feather(canvas, tile, returned, width):
    """
    Cross-fade from the canvas to the generator's copy of the context, ending at the seam.

    Over *width* pixels on the context side of each new seam the canvas pixels are
    blended (smoothstep) towards the returned window, which is continuous with the
    new region at the seam, so a colour or line mismatch becomes a gradual change
    instead of a step. Returns {name: (rect, original pixels)} so a redo can restore them.
    """
    wx0, wy0 = tile["win"][0], tile["win"][1]
    ax0, ay0, ax1, ay1 = tile["acc"]
    left, top = feather_width(tile, width)
    backups = {}

    def ramp(count):
        t = (np.arange(count) + 0.5) / count
        return t * t * (3 - 2 * t)

    if left:
        rect = (ax0 - left, ay0, ax0, ay1)
        original = canvas.pixels[ay0:ay1, ax0 - left:ax0].copy()
        theirs = returned[ay0 - wy0:ay1 - wy0, ax0 - left - wx0:ax0 - wx0].astype(np.float64)
        alpha = ramp(left)[None, :, None]
        canvas.pixels[ay0:ay1, ax0 - left:ax0] = np.clip(original * (1 - alpha) + theirs * alpha + 0.5, 0, 255)
        backups["left"] = (rect, original)
    if top:
        rect = (ax0, ay0 - top, ax1, ay0)
        original = canvas.pixels[ay0 - top:ay0, ax0:ax1].copy()
        theirs = returned[ay0 - top - wy0:ay0 - wy0, ax0 - wx0:ax1 - wx0].astype(np.float64)
        alpha = ramp(top)[:, None, None]
        canvas.pixels[ay0 - top:ay0, ax0:ax1] = np.clip(original * (1 - alpha) + theirs * alpha + 0.5, 0, 255)
        backups["top"] = (rect, original)
    return backups


NAMED_COLOURS = {"white": (255, 255, 255), "black": (0, 0, 0), "grey": (128, 128, 128), "gray": (128, 128, 128)}


def parse_colour(text):
    """
    A colour given as a name (white, black, grey) or #rrggbb.
    """
    text = text.strip().lower()
    if text in NAMED_COLOURS:
        return NAMED_COLOURS[text]
    if len(text) == 7 and text[0] == "#":
        try:
            return (int(text[1:3], 16), int(text[3:5], 16), int(text[5:7], 16))
        except ValueError:
            pass
    raise ValueError("A colour must be white, black, grey or #rrggbb, not '{0}'".format(text))


def has_transparency(image):
    """
    True if a PIL image has any pixel that is not fully opaque.
    """
    if image.mode in ("RGBA", "LA", "PA") or "transparency" in image.info:
        alpha = np.asarray(image.convert("RGBA"))[..., 3]
        return bool(alpha.min() < 255)
    return False


def flatten(image, colour):
    """
    The image composited over a plain colour, as RGB.
    """
    rgba = image.convert("RGBA")
    backdrop = Image.new("RGBA", rgba.size, tuple(colour) + (255,))
    return Image.alpha_composite(backdrop, rgba).convert("RGB")


def restore_alpha(pixels, alpha_image, colour):
    """
    An RGBA array from generated pixels (drawn over *colour*) and the original alpha scaled up.

    The alpha is the original's, enlarged smoothly, so the silhouette cannot change with the
    style. Partly transparent pixels were drawn mixed with the backdrop; that mix is removed
    so the edge does not carry a halo of the backdrop colour when placed on another background.
    """
    height, width = pixels.shape[:2]
    alpha = np.asarray(alpha_image.resize((width, height), Image.BICUBIC), dtype=np.float64) / 255.0
    backdrop = np.array(colour, dtype=np.float64)
    a = np.maximum(alpha, 0.1)[..., None]
    colour_out = (pixels.astype(np.float64) - (1 - alpha[..., None]) * backdrop) / a
    colour_out = np.where(alpha[..., None] >= 0.999, pixels.astype(np.float64), colour_out)
    out = np.empty((height, width, 4), dtype=np.uint8)
    out[..., :3] = np.clip(colour_out + 0.5, 0, 255)
    out[..., 3] = np.clip(alpha * 255 + 0.5, 0, 255)
    return out
