"""
Dependency checking and installation (standard library only, so it works before Pillow exists).
"""

import os
import subprocess
import sys

REQUIREMENTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "requirements.txt")
VENV_ENV = "SCALING_IMAGES_VENV"
CONFIG_ENV = "SCALING_IMAGES_CONFIG_DIR"
RELAUNCHED_ENV = "SCALING_IMAGES_RELAUNCHED"


def config_dir():
    base = os.environ.get(CONFIG_ENV)
    if not base:
        base = os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), "scaling-images")
    return base


def _record_path():
    return os.path.join(config_dir(), "venv")


def venv_python(venv):
    if os.name == "nt":
        return os.path.join(venv, "Scripts", "python.exe")
    return os.path.join(venv, "bin", "python")


def recorded_venv():
    """
    The venv to run under: the environment variable, else the one `setup --venv` recorded.
    """
    venv = os.environ.get(VENV_ENV)
    if not venv:
        try:
            with open(_record_path(), "r") as handle:
                venv = handle.read().strip()
        except IOError:
            return None
    return venv if venv and os.path.exists(venv_python(venv)) else None


def missing_dependencies():
    missing = []
    for module, package in (("PIL", "Pillow"), ("numpy", "numpy")):
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    return missing


def relaunch_if_needed():
    """
    Re-run this command under the recorded venv's Python, if there is one and we are not in it.
    """
    if os.environ.get(RELAUNCHED_ENV):
        return
    venv = recorded_venv()
    if not venv:
        return
    python = venv_python(venv)
    if os.path.realpath(sys.prefix) == os.path.realpath(venv):
        return
    os.environ[RELAUNCHED_ENV] = "1"
    os.execv(python, [python] + sys.argv)


def install_hint(script):
    return ("Missing Python packages: {0}.\n"
            "Install them with:   {1} -m pip install -r {2}\n"
            "or, to use a virtual environment (recommended if that is refused):\n"
            "                     {1} {3} setup --venv ~/.scaling-images-venv".format(
                "{missing}", sys.executable, REQUIREMENTS, script))


def _pip_install(python, extra=None):
    command = [python, "-m", "pip", "install", "-r", REQUIREMENTS] + (extra or [])
    return subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)


def check():
    """
    Print what is present; returns 0 when everything needed is installed.
    """
    problems = missing_dependencies()
    print("python {0} at {1}".format(sys.version.split()[0], sys.executable))
    for module in ("PIL", "numpy"):
        try:
            imported = __import__(module)
            print("{0}: {1}".format(module, getattr(imported, "__version__", "present")))
        except ImportError:
            print("{0}: MISSING".format(module))
    venv = recorded_venv()
    print("virtual environment: {0}".format(venv or "none recorded"))
    return 1 if problems else 0


def main(args, script):
    """
    The `setup` subcommand: --check, or install into this Python or into --venv DIR.
    """
    venv = None
    system_site = False
    check_only = False
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--check":
            check_only = True
        elif arg == "--system-site-packages":
            system_site = True
        elif arg == "--venv" and index + 1 < len(args):
            index += 1
            venv = os.path.abspath(os.path.expanduser(args[index]))
        else:
            print("usage: setup [--check] [--venv DIR [--system-site-packages]]")
            return 1
        index += 1

    if check_only:
        return check()

    if venv:
        import venv as venv_module
        print("Creating the virtual environment {0}".format(venv))
        venv_module.create(venv, with_pip=True, system_site_packages=system_site)
        python = venv_python(venv)
    else:
        python = sys.executable

    result = _pip_install(python)
    print(result.stdout.strip())
    if result.returncode != 0:
        if "externally-managed-environment" in result.stdout:
            print("\nThis Python refuses a global install. Use a virtual environment instead:\n"
                  "  {0} {1} setup --venv ~/.scaling-images-venv".format(sys.executable, script))
        return 1

    if venv:
        os.makedirs(config_dir(), exist_ok=True)
        with open(_record_path(), "w") as handle:
            handle.write(venv + "\n")
        print("\nVirtual environment ready; later runs will use it automatically.\n"
              "(It is recorded in {0}; or set {1}={2}.)".format(_record_path(), VENV_ENV, venv))
    else:
        print("\nDependencies installed.")
    return 0
