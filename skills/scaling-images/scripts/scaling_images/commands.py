"""
The command-line commands: init, next, accept, redo, status, preview, finish, probe, description.
"""

import argparse
import os
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw

from . import __version__
from . import canvas as cv
from . import description as desc
from . import geometry, seams, state as st
from .instructions import build
from .profiles import PROFILE_NAMES, get_profile, Profile

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_REJECTED = 2
EXIT_PAUSED = 3
EXIT_CONFIRM = 4
EXIT_WARNINGS = 5

SEAM_WARN_RATIO = 3.0
CONTEXT_REJECT = 0.5
CONTEXT_WARN = 0.8
SOFT_FRACTION = 0.9
MAX_SHIFT = 64


class CommandError(Exception):
    """A user-facing failure; the message is printed and the exit status is *status*."""

    def __init__(self, message, status=EXIT_ERROR):
        Exception.__init__(self, message)
        self.status = status


def _resolve_work(args):
    work = args.work
    if work is None:
        if st.exists("."):
            work = "."
        else:
            raise CommandError("No state.json here; pass --work DIR (the directory given to init)")
    return work


def _load_source(work, state):
    return Image.open(os.path.join(work, "original.png")).convert("RGB")


def _description_path(work, state):
    path = state["description"]["path"]
    return path if os.path.isabs(path) else os.path.join(work, path)


def _check_description(work, state):
    """
    Pause the run, changing nothing, if the description has been edited.
    """
    path = _description_path(work, state)
    try:
        _, _, text = desc.load(path)
    except desc.DescriptionError as exc:
        raise CommandError("PAUSED: the description cannot be read ({0}). Stop and ask the user.".format(exc),
                           EXIT_PAUSED)
    if desc.description_hash(text) != state["description"]["hash"]:
        raise CommandError(
            "PAUSED: the description '{0}' has changed since this run used it.\n"
            "Do NOT continue and do not edit it yourself. Stop and ask the user, who may have changed it "
            "on purpose (for example for a stylistic effect). Offer these choices:\n"
            "  1. Revert the description to what it was; the run then continues unchanged.\n"
            "  2. Adopt the change from the current tile onwards:  description --adopt\n"
            "     (the style may legitimately differ across the join, so style checks there only warn).\n"
            "  3. Redo from a chosen tile with the new description: "
            "description --adopt --redo-from TILE --yes\n"
            "     (discards that tile and every tile that depended on it).".format(path), EXIT_PAUSED)


def _parse_size(text):
    try:
        w, h = text.lower().split("x")
        return int(w), int(h)
    except ValueError:
        raise CommandError("A size must look like 2560x1920, not '{0}'".format(text))


def _marker_colour(state):
    return tuple(state["marker"]["colour"])


# ---------------------------------------------------------------- init

def cmd_init(args):
    if not os.path.isfile(args.source):
        raise CommandError("The source image '{0}' does not exist".format(args.source))
    source_path = os.path.abspath(args.source)
    stem = os.path.splitext(os.path.basename(source_path))[0]
    work = args.work or os.path.join(os.path.dirname(source_path), stem + "-scaling")

    if st.exists(work) and not args.force:
        raise CommandError("'{0}' already holds a run; use --force to start again (this discards it)".format(work))
    os.makedirs(work, exist_ok=True)

    # Preparation: the source, the description and the scale.
    original = Image.open(source_path)
    source_format = original.format
    source = original.convert("RGB")

    description_path = args.description or os.path.join(work, "description.md")
    try:
        _, _, text = desc.load(description_path)
    except desc.DescriptionError as exc:
        raise CommandError("{0}\nWrite the description first (see references/description-format.md) and have "
                           "the user approve it.".format(exc))

    try:
        target = geometry.target_size(
            source.size, factor=args.factor, target=_parse_size(args.target) if args.target else None)
        profile = get_profile(
            args.profile, tile=args.tile, multiple=args.multiple, max_edge=args.max_edge,
            max_ratio=args.max_ratio, min_pixels=args.min_pixels, max_pixels=args.max_pixels)
        tiles = geometry.plan_grid(target, profile, context=args.context, min_slice=args.min_slice)
    except geometry.GeometryError as exc:
        raise CommandError(str(exc))

    # Construction: marker colour, state and the empty canvas.
    colour_name, colour = cv.choose_marker_colour(source)
    for tile in tiles:
        tile["status"] = "pending"
        tile["warnings"] = []
        tile["seams"] = {}
    state = {
        "version": st.STATE_VERSION,
        "tool_version": __version__,
        "source": source_path,
        "source_format": source_format,
        "source_size": list(source.size),
        "target": list(target),
        "profile": profile.to_dict(),
        "context": args.context if args.context is not None else int(round(profile.tile / 3.0)),
        "marker": {"colour": list(colour), "name": colour_name, "width": args.marker_width},
        "options": {"align": not args.no_align, "tone": not args.no_tone},
        "description": {
            "path": os.path.relpath(os.path.abspath(description_path), os.path.abspath(work)),
            "hash": desc.description_hash(text),
            "history": [{"hash": desc.description_hash(text), "from_tile": 0}],
        },
        "tiles": tiles,
    }

    # Creation: write everything.
    source.save(os.path.join(work, "original.png"))
    cv.Canvas(target).save(work)
    st.save(work, state)

    print("Initialised '{0}': {1}x{2} source ({3}) -> {4}x{5}, {6} tile(s) with profile '{7}'.".format(
        work, source.size[0], source.size[1], source_format, target[0], target[1], len(tiles), profile.name))
    print("Marker colour: {0}.".format(colour_name))
    if not profile.honours_size:
        print("Profile '{0}' does not honour the requested size: run 'probe' before the first tile.".format(
            profile.name))
    print("Next: scale_image.py next --work {0}".format(work))
    return EXIT_OK


# ---------------------------------------------------------------- next

def _locator(source, tile, target, colour):
    image = source.copy()
    sw, sh = image.size
    tw, th = target
    draw = ImageDraw.Draw(image)
    scale_x, scale_y = sw / float(tw), sh / float(th)
    win = [tile["win"][0] * scale_x, tile["win"][1] * scale_y, tile["win"][2] * scale_x, tile["win"][3] * scale_y]
    acc = [tile["acc"][0] * scale_x, tile["acc"][1] * scale_y, tile["acc"][2] * scale_x, tile["acc"][3] * scale_y]
    line = max(2, sw // 200)
    draw.rectangle(win, outline=(255, 255, 255), width=line)
    draw.rectangle(acc, outline=tuple(colour), width=line)
    return image


def _prepare(work, state, tile):
    source = _load_source(work, state)
    canvas = cv.Canvas.load(work)
    directory = st.tile_dir(work, tile)
    os.makedirs(directory, exist_ok=True)

    paths = {
        "input": os.path.join(directory, "input.png"),
        "result": os.path.join(directory, "result.png"),
        "locator": os.path.join(directory, "locator.png"),
        "original": os.path.join(work, "original.png"),
    }
    marker = state["marker"]
    cv.render_input(source, canvas, tile, tuple(marker["colour"]), marker["width"]).save(paths["input"])
    _locator(source, tile, state["target"], marker["colour"]).save(paths["locator"])

    prose, items, _ = desc.load(_description_path(work, state))
    groups = desc.classify(items, tile, state["target"], canvas.mask)
    text = build(state, tile, prose, groups, paths, marker["name"])
    with open(os.path.join(directory, "instructions.txt"), "w") as handle:
        handle.write(text)
    return text


def cmd_next(args):
    work = _resolve_work(args)
    state = st.load(work)
    _check_description(work, state)

    # The previous tile is kept (no longer a candidate for a cheap redo) once we move on.
    for tile in state["tiles"]:
        if tile["status"] == "accepted":
            tile["status"] = "kept"

    tile = st.next_pending(state)
    st.save(work, state)
    if tile is None:
        print("All {0} tiles are accepted. Run: finish --work {1}".format(len(state["tiles"]), work))
        return EXIT_OK

    print(_prepare(work, state, tile))
    return EXIT_OK


# ---------------------------------------------------------------- accept

def _reject(message):
    raise CommandError("REJECTED: {0}\nRegenerate this tile from the same input and run accept again.".format(
        message), EXIT_REJECTED)


def cmd_accept(args):
    work = _resolve_work(args)
    state = st.load(work)
    _check_description(work, state)

    tile = st.next_pending(state)
    if tile is None:
        raise CommandError("There is nothing to accept: every tile is already accepted")
    directory = st.tile_dir(work, tile)
    result_path = args.result or os.path.join(directory, "result.png")
    if not os.path.isfile(result_path):
        raise CommandError("No result at '{0}'. Run 'next' to see where tile {1} must be saved.".format(
            result_path, st.tile_label(tile)))

    warnings = []
    width, height = tile["size"]

    # Preparation: size check, resizing if the shape matches.
    try:
        returned_image = Image.open(result_path).convert("RGB")
    except Exception as exc:
        _reject("the result cannot be read as an image ({0})".format(exc))
    rw, rh = returned_image.size
    if (rw, rh) != (width, height):
        if abs((rw / float(rh)) - (width / float(height))) > 0.01 * (width / float(height)):
            _reject("the result is {0}x{1} but its shape differs from the required {2}x{3}".format(
                rw, rh, width, height))
        fraction = min(rw / float(width), rh / float(height))
        returned_image = returned_image.resize((width, height), Image.LANCZOS)
        warnings.append("the result was {0}x{1}, resized to {2}x{3}".format(rw, rh, width, height))
        if fraction < SOFT_FRACTION:
            warnings.append("it was only {0}% of the required size so this tile is softer than intended; "
                            "consider re-planning with a smaller --tile".format(int(round(fraction * 100))))
    returned = np.array(returned_image)

    # Preparation: what we supplied, and which of its pixels were accepted context.
    source = _load_source(work, state)
    canvas = cv.Canvas.load(work)
    marker = state["marker"]
    colour = tuple(marker["colour"])
    supplied = np.array(cv.render_input(source, canvas, tile, colour, marker["width"]))
    mask = canvas.window_mask(tile)

    if cv_marker_left(returned, tile, colour, marker["width"]):
        _reject("a {0} marker line is still visible in the result; it must be redrawn away".format(marker["name"]))

    # Processing: align, check the context, match tone.
    adopted_here = state["description"]["history"][-1]["from_tile"] == tile["index"] and tile["index"] > 0
    if mask.sum() > 256:
        if state["options"]["align"]:
            dx, dy, peak = seams.estimate_offset(supplied, returned, mask, MAX_SHIFT)
            if peak > 0.1 and (dx or dy):
                returned = seams.align(returned, dx, dy)
                warnings.append("the result was displaced by ({0}, {1}) pixels and has been corrected".format(
                    dx, dy))
        correlation = seams.context_correlation(supplied, returned, mask)
        if correlation < CONTEXT_REJECT and not adopted_here:
            _reject("the redrawn context does not match the supplied context (correlation {0:.2f}); "
                    "the generator has changed or moved the finished artwork".format(correlation))
        if correlation < CONTEXT_WARN:
            warnings.append("the context correlates only {0:.2f} with the supplied one".format(correlation))
        if state["options"]["tone"]:
            returned = seams.tone_match(returned, supplied, mask)

    # Creation: merge, measure the seams, keep evidence.
    cv.merge(canvas, tile, returned)
    report = seams.seam_report(canvas.pixels, tile)
    for name, entry in report.items():
        if entry["ratio"] > SEAM_WARN_RATIO:
            warnings.append("the {0} seam is visible (difference across it {1:.1f} against {2:.1f} nearby)".format(
                name, entry["across"], entry["within"]))
    for name, crop in seams.seam_crops(canvas.pixels, tile).items():
        Image.fromarray(crop).save(os.path.join(directory, "seam-{0}.png".format(name)))

    canvas.save(work)
    tile["status"] = "accepted"
    tile["warnings"] = warnings
    tile["seams"] = report
    tile["description_hash"] = state["description"]["hash"]
    st.save(work, state)

    print("Accepted tile {0} ({1} of {2}).".format(st.tile_label(tile), tile["index"] + 1, len(state["tiles"])))
    for name, entry in sorted(report.items()):
        print("  {0} seam: across {1:.1f}, nearby {2:.1f}, ratio {3:.2f}".format(
            name, entry["across"], entry["within"], entry["ratio"]))
    if report:
        print("  Look at the 1:1 crops in {0} before continuing.".format(directory))
    for warning in warnings:
        print("  WARNING: {0}".format(warning))
    print("Next: scale_image.py next --work {0}".format(work))
    return EXIT_WARNINGS if warnings else EXIT_OK


def cv_marker_left(returned, tile, colour, width):
    return seams.marker_remains(returned, tile, colour, width)


# ---------------------------------------------------------------- redo

def cmd_redo(args):
    work = _resolve_work(args)
    state = st.load(work)
    _check_description(work, state)
    return _redo(work, state, args.tile, args.yes)


def _redo_plan(state, spec, confirmed):
    """
    Work out (and announce) what a redo would discard; refuse unless confirmed.
    """
    tile = st.find_tile(state, spec)
    if tile["status"] == "pending":
        raise CommandError("Tile {0} has not been accepted, so there is nothing to redo".format(st.tile_label(tile)))

    later = geometry.dependents(state["tiles"], tile["index"])
    affected = [tile["index"]] + [i for i in later if state["tiles"][i]["status"] != "pending"]
    print("Redoing {0} discards {1} tile(s): {2}".format(
        st.tile_label(tile), len(affected), ", ".join(st.tile_label(state["tiles"][i]) for i in affected)))
    if not confirmed:
        raise CommandError("Not done. Tell the user which tiles would be discarded and, if they agree, "
                           "re-run with --yes.", EXIT_CONFIRM)
    return affected


def _redo(work, state, spec, confirmed):
    affected = _redo_plan(state, spec, confirmed)
    _discard(work, state, affected)
    print("Done. Run: next --work {0}".format(work))
    return EXIT_OK


def _discard(work, state, affected):
    canvas = cv.Canvas.load(work)
    for index in affected:
        entry = state["tiles"][index]
        x0, y0, x1, y1 = entry["acc"]
        canvas.mask[y0:y1, x0:x1] = False
        entry["status"] = "pending"
        entry["warnings"] = []
        entry["seams"] = {}
        entry.pop("description_hash", None)
    canvas.save(work)
    st.save(work, state)


# ---------------------------------------------------------------- status / preview / finish

def _summary(state):
    counts = {}
    for tile in state["tiles"]:
        counts[tile["status"]] = counts.get(tile["status"], 0) + 1
    return counts


def cmd_status(args):
    work = _resolve_work(args)
    state = st.load(work)
    print("Source: {0} ({1}x{2}) -> {3}x{4}".format(
        state["source"], state["source_size"][0], state["source_size"][1], state["target"][0], state["target"][1]))
    print("Profile: {0}, tile {1}, marker {2}".format(
        state["profile"]["name"], state["profile"]["tile"], state["marker"]["name"]))
    for tile in state["tiles"]:
        print("  {0} [{1}] accepted {2} window {3} size {4}x{5}{6}".format(
            st.tile_label(tile), tile["status"], tile["acc"], tile["win"], tile["size"][0], tile["size"][1],
            "  warnings: " + "; ".join(tile["warnings"]) if tile.get("warnings") else ""))
    try:
        _check_description(work, state)
        print("Description: unchanged")
    except CommandError as exc:
        print(str(exc).split("\n")[0])
    return EXIT_OK


def _preview_image(work, state, canvas):
    tw, th = state["target"]
    image = Image.fromarray(canvas.pixels.copy())
    dim = np.array(image)
    dim[~canvas.mask] = (dim[~canvas.mask] * 0.25 + 40).astype(np.uint8)
    image = Image.fromarray(dim)
    draw = ImageDraw.Draw(image)
    line = max(1, tw // 600)
    for tile in state["tiles"]:
        draw.rectangle(tile["acc"], outline=(255, 255, 255), width=line)
    image.thumbnail((1280, 1280))
    return image


def cmd_preview(args):
    work = _resolve_work(args)
    state = st.load(work)
    canvas = cv.Canvas.load(work)
    path = os.path.join(work, "preview.png")
    _preview_image(work, state, canvas).save(path)
    print("Preview: {0} (tile edges outlined; unaccepted areas dimmed)".format(path))
    print("Tiles: {0}".format(", ".join("{0}={1}".format(k, v) for k, v in sorted(_summary(state).items()))))
    for tile in state["tiles"]:
        for name, entry in sorted(tile.get("seams", {}).items()):
            print("  {0} {1} seam: ratio {2:.2f}{3}".format(
                st.tile_label(tile), name, entry["ratio"], "  <-- visible" if entry["ratio"] > SEAM_WARN_RATIO else ""))
    return EXIT_OK


def cmd_finish(args):
    work = _resolve_work(args)
    state = st.load(work)
    _check_description(work, state)
    pending = [st.tile_label(t) for t in state["tiles"] if t["status"] == "pending"]
    if pending:
        raise CommandError("Not finished: tiles still to do: {0}".format(", ".join(pending)))

    canvas = cv.Canvas.load(work)
    stem = os.path.splitext(os.path.basename(state["source"]))[0]
    output = args.output or os.path.join(work, "{0}-{1}x{2}.png".format(stem, state["target"][0], state["target"][1]))
    Image.fromarray(canvas.pixels).save(output)
    _preview_image(work, state, canvas).save(os.path.join(work, "preview.png"))
    print("Wrote {0} ({1}x{2}).".format(output, state["target"][0], state["target"][1]))
    return cmd_preview(args)


# ---------------------------------------------------------------- probe

def cmd_probe(args):
    work = _resolve_work(args)
    state = st.load(work)
    directory = os.path.join(work, "probe")
    os.makedirs(directory, exist_ok=True)
    profile = state["profile"]

    if args.result:
        image = Image.open(args.result)
        dw, dh = image.size
        asked = state["probe"]["asked"]
        fraction = min(dw / float(asked[0]), dh / float(asked[1]))
        multiple = profile["multiple"]
        recommended = (min(dw, dh) // multiple) * multiple
        state["probe"]["delivered"] = [dw, dh]
        st.save(work, state)
        print("Asked for {0}x{1}, delivered {2}x{3} ({4}% of the request).".format(
            asked[0], asked[1], dw, dh, int(round(fraction * 100))))
        if fraction >= 0.95 and abs(dw / float(dh) - asked[0] / float(asked[1])) < 0.02:
            print("The requested size is honoured: keep --tile {0}.".format(profile["tile"]))
        else:
            print("The size is not honoured. Re-run init with --force --tile {0} so that windows are no "
                  "larger than the generator delivers.".format(recommended))
            if abs(dw / float(dh) - asked[0] / float(asked[1])) >= 0.02:
                print("The shape also changed: the generator may not keep the aspect ratio of the input, "
                      "so tiles of other shapes may be rejected.")
        return EXIT_OK

    size = min(profile["tile"], state["target"][0], state["target"][1])
    size = (size // profile["multiple"]) * profile["multiple"]
    source = _load_source(work, state)
    scale = state["target"][0] / float(state["source_size"][0])
    crop = source.crop((0, 0, int(round(size / scale)), int(round(size / scale))))
    probe_input = crop.resize((size, size), Image.NEAREST)
    input_path = os.path.join(directory, "input.png")
    probe_input.save(input_path)
    state["probe"] = {"asked": [size, size]}
    st.save(work, state)
    print("PROBE (no tile is accepted by this).\n"
          "Redraw '{0}' at higher quality, asking for exactly {1}x{1} pixels if your tool lets you choose, and "
          "save it to '{2}'. Then run: probe --result {2}".format(
              input_path, size, os.path.join(directory, "result.png")))
    return EXIT_OK


# ---------------------------------------------------------------- description

def cmd_description(args):
    work = _resolve_work(args)
    state = st.load(work)
    path = _description_path(work, state)
    try:
        _, _, text = desc.load(path)
    except desc.DescriptionError as exc:
        raise CommandError(str(exc))
    current = desc.description_hash(text)
    changed = current != state["description"]["hash"]

    if not args.adopt:
        print("Description {0}.".format("HAS CHANGED since the run used it" if changed else "is unchanged"))
        return EXIT_PAUSED if changed else EXIT_OK
    if not changed:
        print("Nothing to adopt: the description is unchanged.")
        return EXIT_OK

    first = st.next_pending(state)
    start = first["index"] if first else len(state["tiles"])
    if args.redo_from is not None:
        # Confirm first, so a refusal leaves the run paused with nothing changed.
        affected = _redo_plan(state, args.redo_from, args.yes)
        spec_tile = st.find_tile(state, args.redo_from)
        state["description"]["hash"] = current
        state["description"]["history"].append({"hash": current, "from_tile": spec_tile["index"]})
        _discard(work, state, affected)
        print("Adopted the new description from tile {0}. Run: next --work {1}".format(
            st.tile_label(spec_tile), work))
        return EXIT_OK

    state["description"]["hash"] = current
    state["description"]["history"].append({"hash": current, "from_tile": start})
    st.save(work, state)
    print("Adopted the new description from tile {0} onwards.".format(start))
    return EXIT_OK


# ---------------------------------------------------------------- parser

def build_parser():
    parser = argparse.ArgumentParser(prog="scale_image.py", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command")

    def common(p):
        p.add_argument("--work", help="the work directory given to init (default: the current directory)")

    p = sub.add_parser("init", help="start a run for a source image")
    p.add_argument("source")
    p.add_argument("--factor", type=float)
    p.add_argument("--target", help="target size, WxH")
    p.add_argument("--profile", choices=PROFILE_NAMES, default="gpt-image-2-api")
    p.add_argument("--tile", type=int)
    p.add_argument("--context", type=int)
    p.add_argument("--min-slice", type=int)
    p.add_argument("--marker-width", type=int, default=6)
    p.add_argument("--multiple", type=int)
    p.add_argument("--max-edge", type=int)
    p.add_argument("--max-ratio", type=float)
    p.add_argument("--min-pixels", type=int)
    p.add_argument("--max-pixels", type=int)
    p.add_argument("--no-align", action="store_true")
    p.add_argument("--no-tone", action="store_true")
    p.add_argument("--description")
    p.add_argument("--force", action="store_true")
    common(p)
    p.set_defaults(func=cmd_init)

    for name, func, text in (("next", cmd_next, "prepare the next tile and print its instructions"),
                             ("status", cmd_status, "show progress"),
                             ("preview", cmd_preview, "write a downscaled preview and the seam report"),
                             ("finish", cmd_finish, "write the final PNG")):
        p = sub.add_parser(name, help=text)
        common(p)
        if name == "finish":
            p.add_argument("--output")
        p.set_defaults(func=func)

    p = sub.add_parser("accept", help="validate and merge the generated tile")
    p.add_argument("result", nargs="?", help="the generated image (default: the path 'next' gave)")
    common(p)
    p.set_defaults(func=cmd_accept)

    p = sub.add_parser("redo", help="discard a tile and the tiles that depended on it")
    p.add_argument("tile", help="a tile index or label such as r1c0")
    p.add_argument("--yes", action="store_true", help="confirm the discard (only after the user agrees)")
    common(p)
    p.set_defaults(func=cmd_redo)

    p = sub.add_parser("probe", help="learn what size a generator delivers")
    p.add_argument("--result")
    common(p)
    p.set_defaults(func=cmd_probe)

    p = sub.add_parser("description", help="check or adopt an edited description")
    p.add_argument("--adopt", action="store_true")
    p.add_argument("--redo-from")
    p.add_argument("--yes", action="store_true")
    common(p)
    p.set_defaults(func=cmd_description)
    return parser


def main(argv):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return EXIT_ERROR
    try:
        return args.func(args)
    except (CommandError, st.StateError) as exc:
        print(str(exc), file=sys.stderr)
        return getattr(exc, "status", EXIT_ERROR)
