"""
Generator profiles: the size rules of an image generator.

The scripts cannot detect which generator an agent has, so the agent names a
profile. The figures are defaults researched from public sources (see
references/generator-profiles.md) and can all be overridden for 'custom'.
"""

from .geometry import GeometryError


class Profile(object):
    def __init__(self, name, tile, multiple=16, max_edge=3840, max_ratio=3.0,
                 min_pixels=655360, max_pixels=8294400, honours_size=True):
        self.name = name
        self.tile = tile
        self.multiple = multiple
        self.max_edge = max_edge
        self.max_ratio = max_ratio
        self.min_pixels = min_pixels
        self.max_pixels = max_pixels
        self.honours_size = honours_size

    def check_window(self, width, height):
        """
        Raise GeometryError if a window of this size breaks the generator's rules.
        """
        problems = []
        if width % self.multiple or height % self.multiple:
            problems.append("each edge must be a multiple of {0}".format(self.multiple))
        if max(width, height) > self.max_edge:
            problems.append("the long edge is over {0}".format(self.max_edge))
        if max(width, height) > self.max_ratio * min(width, height):
            problems.append("the aspect ratio is over {0}:1".format(self.max_ratio))
        pixels = width * height
        if pixels > self.max_pixels:
            problems.append("it has more than {0} pixels".format(self.max_pixels))
        if pixels < self.min_pixels:
            problems.append("it has fewer than {0} pixels (use a larger scale)".format(self.min_pixels))
        if problems:
            raise GeometryError("A {0}x{1} window is not allowed by profile '{2}': {3}".format(
                width, height, self.name, "; ".join(problems)))

    def to_dict(self):
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


def get_profile(name, tile=None, **overrides):
    """
    Return the named profile; for 'custom' every rule may be overridden.
    """
    if name == "gpt-image-2-api":
        profile = Profile(name, tile=2048)
    elif name == "codex-builtin":
        # The built-in tool ignores the size (observed: about 1.57 megapixels, 1254x1254 square); use `probe`.
        profile = Profile(name, tile=1248, honours_size=False)
    elif name == "custom":
        profile = Profile(name, tile=2048)
    else:
        raise GeometryError("Unknown profile '{0}' (use gpt-image-2-api, codex-builtin or custom)".format(name))

    for key, value in overrides.items():
        if value is not None:
            setattr(profile, key, value)
    if tile:
        profile.tile = tile
    return profile


PROFILE_NAMES = ["gpt-image-2-api", "codex-builtin", "custom"]
