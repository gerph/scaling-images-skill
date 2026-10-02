"""
Synthetic images and a fake generator, so the skill is tested with no real generator.
"""

import numpy as np
from PIL import Image


def ideal_image(size, seed=1):
    """
    A textured, smoothly varying RGB image of *size*, standing in for the perfect enlargement.
    """
    w, h = size
    rng = np.random.RandomState(seed)
    base = rng.rand(max(2, h // 64), max(2, w // 64), 3) * 255
    smooth = np.asarray(Image.fromarray(base.astype(np.uint8)).resize((w, h), Image.BICUBIC), dtype=np.float64)
    fine = np.asarray(Image.fromarray((rng.rand(h // 4 + 1, w // 4 + 1, 3) * 255).astype(np.uint8)).resize(
        (w, h), Image.BICUBIC), dtype=np.float64)
    xs = np.arange(w)[None, :, None]
    ys = np.arange(h)[:, None, None]
    ramp = (xs * 0.05 + ys * 0.03) % 255
    out = smooth * 0.6 + fine * 0.25 + ramp * 0.15
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


class FakeGenerator(object):
    """
    Returns the ideal image's window for a tile, with optional defects.
    """

    def __init__(self, ideal):
        self.ideal = np.asarray(ideal.convert("RGB"))

    def generate(self, tile, shift=None, tone=None, resize=None, marker=None, scramble_context=False):
        x0, y0, x1, y1 = tile["win"]
        window = self.ideal[y0:y1, x0:x1].copy()
        pad_x, pad_y = tile["pad"]
        if pad_x or pad_y:
            window = np.pad(window, ((0, pad_y), (0, pad_x), (0, 0)), mode="edge")

        if scramble_context:
            window = window[::-1, ::-1].copy()
        if shift:
            dx, dy = shift
            padded = np.pad(window, ((abs(dy), abs(dy)), (abs(dx), abs(dx)), (0, 0)), mode="edge")
            window = padded[abs(dy) - dy:abs(dy) - dy + window.shape[0],
                            abs(dx) - dx:abs(dx) - dx + window.shape[1]].copy()
        if tone:
            gain, offset = tone
            window = np.clip(window.astype(np.float64) * gain + offset, 0, 255).astype(np.uint8)
        if marker:
            colour, width = marker
            ux = tile["acc"][0] - x0 if tile["marker_left"] else 0
            uy = tile["acc"][1] - y0 if tile["marker_top"] else 0
            if tile["marker_left"]:
                window[uy:, ux:ux + width] = colour
            if tile["marker_top"]:
                window[uy:uy + width, ux:] = colour

        image = Image.fromarray(window)
        if resize:
            image = image.resize(resize, Image.LANCZOS)
        return image
