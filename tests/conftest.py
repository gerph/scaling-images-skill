import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPTS = os.path.join(ROOT, "skills", "scaling-images", "scripts")
for path in (SCRIPTS, HERE):
    if path not in sys.path:
        sys.path.insert(0, path)
