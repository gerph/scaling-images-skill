"""
The state file: everything needed to resume a run in a later session.
"""

import json
import os

STATE_NAME = "state.json"
STATE_VERSION = 1


class StateError(Exception):
    """The work directory has no usable state."""


def state_path(work):
    return os.path.join(work, STATE_NAME)


def exists(work):
    return os.path.isfile(state_path(work))


def load(work):
    try:
        with open(state_path(work), "r") as handle:
            state = json.load(handle)
    except (IOError, ValueError) as exc:
        raise StateError("No usable state in '{0}': {1}. Run 'init' first (or pass --work).".format(work, exc))
    if state.get("version") != STATE_VERSION:
        raise StateError("State file version {0} is not supported".format(state.get("version")))
    return state


def save(work, state):
    """
    Write the state atomically (write then rename).
    """
    path = state_path(work)
    temp = path + ".tmp"
    with open(temp, "w") as handle:
        json.dump(state, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temp, path)


def tile_dir(work, tile):
    return os.path.join(work, "tiles", "r{0}c{1}".format(tile["row"], tile["col"]))


def tile_label(tile):
    return "r{0}c{1}".format(tile["row"], tile["col"])


def find_tile(state, spec):
    """
    Resolve a tile given as an index ('3') or a label ('r1c0').
    """
    spec = str(spec).strip().lower()
    for tile in state["tiles"]:
        if spec == str(tile["index"]) or spec == tile_label(tile):
            return tile
    raise StateError("There is no tile '{0}'".format(spec))


def next_pending(state):
    for tile in state["tiles"]:
        if tile["status"] == "pending":
            return tile
    return None
