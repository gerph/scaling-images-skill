#!/usr/bin/env python3
"""
Scale an image far beyond a generator's size limit, one tile at a time.

Run with no arguments, or 'help', for the commands. Author: Charles Ferguson (Gerph). Licence: MIT.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from scaling_images import __version__, installer  # noqa: E402


def main(argv):
    script = os.path.abspath(__file__)
    if argv and argv[0] in ("--version", "-V"):
        print(__version__)
        return 0
    if argv and argv[0] == "setup":
        return installer.main(argv[1:], script)

    installer.relaunch_if_needed()
    missing = installer.missing_dependencies()
    if missing:
        print(installer.install_hint(script).replace("{missing}", ", ".join(missing)), file=sys.stderr)
        return 1

    from scaling_images import commands
    return commands.main(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
