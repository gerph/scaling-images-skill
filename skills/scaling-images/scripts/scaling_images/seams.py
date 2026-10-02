"""
Seam measurement, alignment, tone matching and the checks run on a returned tile.
"""

import numpy as np

from .canvas import unknown_origin


def luminance(array):
    return array[..., 0] * 0.299 + array[..., 1] * 0.587 + array[..., 2] * 0.114


def _band_difference(a, b):
    return float(np.abs(a.astype(np.float64) - b.astype(np.float64)).mean())


def seam_report(pixels, tile):
    """
    How visible each of a tile's new seams is, from the canvas after merging.

    For a seam, the mean difference between the two pixels either side of the join
    ("across") is compared with the same measure between neighbouring pixels away
    from the join ("within"); a ratio well above 1 means a visible line.
    """
    ax0, ay0, ax1, ay1 = tile["acc"]
    report = {}
    if tile["marker_left"] and ax0 >= 3 and ax1 - ax0 >= 6:
        across = _band_difference(pixels[ay0:ay1, ax0 - 1], pixels[ay0:ay1, ax0])
        within = (_band_difference(pixels[ay0:ay1, ax0 + 2:ax0 + 5], pixels[ay0:ay1, ax0 + 3:ax0 + 6])
                  + _band_difference(pixels[ay0:ay1, ax0 - 4:ax0 - 1], pixels[ay0:ay1, ax0 - 3:ax0])) / 2.0
        report["left"] = {"across": across, "within": within, "ratio": across / max(within, 1.0)}
    if tile["marker_top"] and ay0 >= 3 and ay1 - ay0 >= 6:
        across = _band_difference(pixels[ay0 - 1, ax0:ax1], pixels[ay0, ax0:ax1])
        within = (_band_difference(pixels[ay0 + 2:ay0 + 5, ax0:ax1], pixels[ay0 + 3:ay0 + 6, ax0:ax1])
                  + _band_difference(pixels[ay0 - 4:ay0 - 1, ax0:ax1], pixels[ay0 - 3:ay0, ax0:ax1])) / 2.0
        report["top"] = {"across": across, "within": within, "ratio": across / max(within, 1.0)}
    return report


def seam_crops(pixels, tile, half=128):
    """
    1:1 crops centred on each new seam, as numpy arrays keyed 'left' and 'top'.
    """
    ax0, ay0, ax1, ay1 = tile["acc"]
    h, w = pixels.shape[:2]
    crops = {}
    if tile["marker_left"]:
        crops["left"] = pixels[ay0:min(ay1, ay0 + 4 * half), max(0, ax0 - half):min(w, ax0 + half)]
    if tile["marker_top"]:
        crops["top"] = pixels[max(0, ay0 - half):min(h, ay0 + half), ax0:min(ax1, ax0 + 4 * half)]
    return crops


def _masked_lum(array, mask):
    lum = luminance(array.astype(np.float64))
    if not mask.any():
        return lum * 0
    lum = lum - lum[mask].mean()
    lum[~mask] = 0
    return lum


def estimate_offset(supplied, returned, mask, max_shift=64):
    """
    The integer (dx, dy) by which *returned* content is displaced from *supplied*.

    Phase correlation over the accepted (context) pixels only. Returns
    (dx, dy, peak) where peak is 0 to 1 (higher is a clearer match).
    """
    a = _masked_lum(supplied, mask)
    b = _masked_lum(returned, mask)
    cross = np.fft.fft2(b) * np.conj(np.fft.fft2(a))
    cross /= np.maximum(np.abs(cross), 1e-9)
    corr = np.fft.ifft2(cross).real
    h, w = corr.shape
    # Restrict to plausible shifts (wrapped).
    limit_y, limit_x = min(max_shift, h // 2), min(max_shift, w // 2)
    window = np.full(corr.shape, -1.0)
    ys = np.r_[0:limit_y + 1, h - limit_y:h]
    xs = np.r_[0:limit_x + 1, w - limit_x:w]
    window[np.ix_(ys, xs)] = corr[np.ix_(ys, xs)]
    index = int(np.argmax(window))
    py, px = divmod(index, w)
    dy = py if py <= h // 2 else py - h
    dx = px if px <= w // 2 else px - w
    return dx, dy, float(window[py, px])


def align(returned, dx, dy):
    """
    Shift a returned window by (-dx, -dy) so its content matches the supplied one.
    """
    if dx == 0 and dy == 0:
        return returned
    h, w = returned.shape[:2]
    padded = np.pad(returned, ((abs(dy), abs(dy)), (abs(dx), abs(dx)), (0, 0)), mode="edge")
    y0 = abs(dy) + dy
    x0 = abs(dx) + dx
    return padded[y0:y0 + h, x0:x0 + w].copy()


def context_correlation(supplied, returned, mask):
    """
    Normalised correlation of luminance over the context pixels (-1 to 1).
    """
    a = luminance(supplied.astype(np.float64))[mask]
    b = luminance(returned.astype(np.float64))[mask]
    if a.size < 16 or a.std() < 1e-6 or b.std() < 1e-6:
        return 1.0 if np.allclose(a, b, atol=2) else 0.0
    return float(np.corrcoef(a, b)[0, 1])


def tone_match(returned, supplied, mask):
    """
    Correct a returned window's tone so its copy of the context matches ours.

    A per-channel gain (clamped to 0.7 to 1.4) and offset from the mean and
    spread of the context pixels, applied to the whole window.
    """
    if mask.sum() < 64:
        return returned
    out = returned.astype(np.float64)
    for channel in range(3):
        ours = supplied[..., channel][mask].astype(np.float64)
        theirs = returned[..., channel][mask].astype(np.float64)
        gain = ours.std() / theirs.std() if theirs.std() > 1e-6 else 1.0
        gain = min(1.4, max(0.7, gain))
        out[..., channel] = (out[..., channel] - theirs.mean()) * gain + ours.mean()
    return np.clip(out + 0.5, 0, 255).astype(np.uint8)


def marker_remains(returned, tile, colour, width, tolerance=60):
    """
    True when a marker line has been left in the returned window.
    """
    ux, uy = unknown_origin(tile)
    near = np.sqrt(((returned.astype(np.int32) - np.array(colour)) ** 2).sum(axis=2)) < tolerance
    fractions = []
    if tile["marker_left"]:
        fractions.append(float(near[uy:, ux:ux + width].mean()))
    if tile["marker_top"]:
        fractions.append(float(near[uy:uy + width, ux:].mean()))
    return any(f > 0.5 for f in fractions)


def _smooth_1d(values, sigma):
    """
    Gaussian smoothing along axis 0 of an (N, 3) array, with edge replication.
    """
    radius = max(1, int(sigma * 3))
    x = np.arange(-radius, radius + 1)
    kernel = np.exp(-x ** 2 / (2.0 * sigma ** 2))
    kernel /= kernel.sum()
    padded = np.pad(values, ((radius, radius), (0, 0)), mode="edge")
    return np.stack([np.convolve(padded[:, c], kernel, "valid") for c in range(3)], axis=1)


def tone_field(returned, supplied, tile, band=160, sigma=24, reach=(0, 0)):
    """
    Correct the generator's colour drift in the new region from its copy of the context.

    A generator often changes colour and contrast differently from top to bottom
    (a vertical gradient), which a single gain and offset cannot undo. For a left
    seam, the per-row mean difference between our context and the generator's copy
    just left of the seam is smoothed and added to the new region (every column
    right of the seam); for a top seam, the same per column. Only the new region
    changes, plus *reach* (left, top) pixels of context beside the seam, so that a feather
    blends towards a copy whose colour already agrees with the canvas.
    """
    ux, uy = unknown_origin(tile)
    out = returned.astype(np.float64)
    supplied = supplied.astype(np.float64)

    if tile["marker_left"] and ux >= 16:
        x0 = max(0, ux - band)
        diff = (supplied[uy:, x0:ux] - out[uy:, x0:ux]).mean(axis=1)
        out[uy:, ux - min(reach[0], ux):] += _smooth_1d(diff, sigma)[:, None, :]

    if tile["marker_top"] and uy >= 16:
        y0 = max(0, uy - band)
        diff = (supplied[y0:uy, ux:] - out[y0:uy, ux:]).mean(axis=0)
        out[uy - min(reach[1], uy):, ux:] += _smooth_1d(diff, sigma)[None, :, :]

    return np.clip(out + 0.5, 0, 255).astype(np.uint8)
