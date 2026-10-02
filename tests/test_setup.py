import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "skills", "scaling-images", "scripts", "scale_image.py")


def run(args, env_extra=None, cwd=None):
    env = dict(os.environ)
    env.update(env_extra or {})
    env.pop("SCALING_IMAGES_RELAUNCHED", None)
    result = subprocess.run([sys.executable, SCRIPT] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            universal_newlines=True, env=env, cwd=cwd)
    return result.returncode, result.stdout, result.stderr


def test_version():
    status, out, err = run(["--version"])
    assert status == 0 and out.strip() == "0.1.0"


def test_missing_pillow_prints_the_install_command(tmp_path):
    fake = tmp_path / "PIL"
    fake.mkdir()
    (fake / "__init__.py").write_text("raise ImportError('hidden for the test')\n")
    status, out, err = run(["status"], {"PYTHONPATH": str(tmp_path), "SCALING_IMAGES_CONFIG_DIR": str(tmp_path / "cfg")})
    assert status == 1
    assert "Missing Python packages: Pillow" in err
    assert "-m pip install -r" in err and "setup --venv" in err


def test_setup_check_reports_versions():
    status, out, err = run(["setup", "--check"])
    assert status == 0 and "PIL:" in out and "numpy:" in out


def test_setup_venv_creates_and_is_used_afterwards(tmp_path):
    venv = tmp_path / "venv"
    env = {"SCALING_IMAGES_CONFIG_DIR": str(tmp_path / "cfg")}
    # --system-site-packages lets the install succeed offline: the packages are already present.
    status, out, err = run(["setup", "--venv", str(venv), "--system-site-packages"], env)
    assert status == 0, out + err
    assert os.path.isfile(str(tmp_path / "cfg" / "venv"))

    status, out, err = run(["setup", "--check"], env)
    assert status == 0 and str(venv) in out
    # The recorded venv's Python is the one that runs.
    status, out, err = run(["status", "--work", str(tmp_path)], env)
    assert "No usable state" in err
