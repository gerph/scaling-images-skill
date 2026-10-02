"""
Package test: only the files the skill ships, in a clean directory, must be enough.
"""

import os
import re
import shutil
import subprocess
import sys

import pytest

from helpers import DESCRIPTION
from synth import ideal_image

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.join(os.path.dirname(HERE), "skills", "scaling-images")


def shipped_copy(tmp_path):
    destination = str(tmp_path / "skills" / "scaling-images")
    shutil.copytree(SKILL, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return destination


def test_skill_header_is_valid():
    text = open(os.path.join(SKILL, "SKILL.md")).read()
    header = text.split("---")[1]
    fields = dict(re.findall(r"^(\w+): (.*)$", header, re.M))
    assert fields["name"] == "scaling-images" == os.path.basename(SKILL)
    assert 20 < len(fields["description"]) <= 1024
    assert "author" in header and "license: MIT" in header
    assert len(text.splitlines()) < 500


def test_skill_links_only_shipped_files(tmp_path):
    copy = shipped_copy(tmp_path)
    for name in ("SKILL.md",):
        text = open(os.path.join(copy, name)).read()
        for target in re.findall(r"\]\(([^)#]+)\)", text):
            assert os.path.isfile(os.path.join(copy, target)), target
    # No reference may point outside the skill.
    for root, _, files in os.walk(copy):
        for name in files:
            if name.endswith(".md"):
                assert "design/" not in open(os.path.join(root, name)).read()


def test_shipped_copy_runs_a_small_job_with_a_venv(tmp_path):
    copy = shipped_copy(tmp_path)
    script = os.path.join(copy, "scripts", "scale_image.py")
    env = dict(os.environ, SCALING_IMAGES_CONFIG_DIR=str(tmp_path / "cfg"))
    env.pop("SCALING_IMAGES_RELAUNCHED", None)

    def call(*args):
        return subprocess.run([sys.executable, script] + [str(a) for a in args], env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    result = call("setup", "--venv", tmp_path / "venv", "--system-site-packages")
    assert result.returncode == 0, result.stdout + result.stderr

    work = tmp_path / "work"
    work.mkdir()
    (work / "description.md").write_text(DESCRIPTION)
    source = tmp_path / "s.png"
    ideal_image((256, 256)).save(str(source))
    result = call("init", source, "--factor", 4, "--profile", "custom", "--tile", 512, "--min-pixels", 1,
                  "--work", work)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (work / "state.json").is_file()
    result = call("next", "--work", work)
    assert result.returncode == 0 and "TILE r0c0" in result.stdout
