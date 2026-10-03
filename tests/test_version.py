import os
import re

from scaling_images import __version__

HERE = os.path.dirname(os.path.abspath(__file__))
CHANGELOG = os.path.join(os.path.dirname(HERE), "CHANGELOG.md")


def test_changelog_names_the_current_version():
    text = open(CHANGELOG).read()
    first = re.search(r"^## (\d+\.\d+\.\d+)\b", text, re.M)
    assert first and first.group(1) == __version__


def test_version_is_plain_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__)
