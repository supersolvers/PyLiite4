"""Run every example in examples/ as a program, and type check it with mypy --strict. See tests/run_example.py."""

import importlib.util
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

import PyLiite4

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
RUNNER = Path(__file__).with_name("run_example.py")
NAMES = ["app", "template", "resources", "translations", "listview", "chat", "preferences", "testing"]


def run(script: Path, **extra_env: str) -> str:
    # As in test_demos.py: a private bus with portals off and GDK on X11, so nothing reaches the desktop.
    command = [sys.executable, str(RUNNER), str(script)]
    if shutil.which("dbus-run-session"):
        command = ["dbus-run-session", "--", *command]
    env = {**os.environ, "GSETTINGS_BACKEND": "memory", "GTK_A11Y": "none", "GDK_DEBUG": "no-portals",
           "ADW_DISABLE_PORTAL": "1", **extra_env}
    if env.get("GDK_BACKEND") != "wayland":
        env.pop("WAYLAND_DISPLAY", None)
        env["GDK_BACKEND"] = "x11"
    with tempfile.TemporaryFile("w+") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
        try:
            returncode = process.wait(timeout=60)
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        log.seek(0)
        output = log.read()
        assert returncode == 0, output[-4000:]
        return output


@pytest.mark.parametrize("name", ["template", "resources", "listview", "chat", "preferences"])
def test_example_runs(name):
    run(EXAMPLES / name / "main.py")


def test_testing_example_passes_its_own_tests():
    # Its pyproject.toml turns PyLiite4.testing on; outside an install, name the plugin.
    from importlib import metadata

    plugin = [] if metadata.entry_points(group="pytest11", name="pyliite4") else ["-p", "PyLiite4.testing"]
    package = Path(PyLiite4.__file__).resolve().parent.parent
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(filter(None, [str(package), os.environ.get("PYTHONPATH")]))}
    env.pop("PYTEST_ADDOPTS", None)
    result = subprocess.run([sys.executable, "-m", "pytest", *plugin, "-q", "--no-header", "-p", "no:cacheprovider",
                             "-W", "ignore::DeprecationWarning"], cwd=EXAMPLES / "testing", env=env,
                            capture_output=True, text=True, timeout=300)
    assert result.returncode == 0 and "5 passed" in result.stdout, result.stdout[-4000:] + result.stderr[-2000:]


def test_app_without_schema(tmp_path):
    # A copy without gschemas.compiled, in case one was compiled next to the example.
    shutil.copytree(EXAMPLES / "app", tmp_path / "app", ignore=shutil.ignore_patterns("gschemas.compiled"))
    output = run(tmp_path / "app" / "main.py")
    assert "won't be saved" in output


def test_app_with_schema(tmp_path):
    compiler = shutil.which("glib-compile-schemas")
    if compiler is None:
        pytest.skip("needs glib-compile-schemas")
    app = tmp_path / "app"
    shutil.copytree(EXAMPLES / "app", app, ignore=shutil.ignore_patterns("gschemas.compiled"))
    subprocess.run([compiler, str(app)], check=True)
    # The memory backend starts empty in each process, so give the size as a keyfile backend's stored value.
    keyfile = tmp_path / "glib-2.0" / "settings" / "keyfile"
    keyfile.parent.mkdir(parents=True)
    keyfile.write_text("[org/example/PyLiite4App]\nwindow-width=777\nwindow-height=555\n")
    output = run(app / "main.py", GSETTINGS_BACKEND="keyfile", XDG_CONFIG_HOME=str(tmp_path),
                 EXAMPLE_EXPECT_SIZE="777x555")
    assert "won't be saved" not in output


def utf8_locale() -> str | None:
    try:
        names = subprocess.run(["locale", "-a"], capture_output=True, text=True).stdout.split()
    except OSError:
        return None
    usable = [name for name in names if name.lower().endswith(("utf8", "utf-8")) and not name.startswith("C.")]
    return next((name for name in usable if name.startswith("en_US")), usable[0] if usable else None)


def test_translations_untranslated():
    run(EXAMPLES / "translations" / "main.py", LANGUAGE="", LC_ALL="C.UTF-8",
        EXAMPLE_EXPECT_TEXT="Translations|Hello, world!|You greeted 1 time")


def test_translations_in_german():
    # LANGUAGE picks the catalogue, but glibc ignores it in the C locale, so LANG needs a real one.
    locale = utf8_locale()
    if locale is None:
        pytest.skip("no UTF-8 locale other than C is installed")
    output = run(EXAMPLES / "translations" / "main.py", LANGUAGE="de", LANG=locale, LC_ALL="", LC_MESSAGES="",
                 # The window title and greeting come from Python, the rest from the .ui file.
                 EXAMPLE_EXPECT_TEXT="Übersetzungen|Hallo, Welt!|Diese Zeile kommt aus der .ui-Datei."
                                     "|Du hast 1 Mal gegrüßt")
    assert "Hello, world!" not in output


@pytest.mark.skipif(importlib.util.find_spec("mypy") is None, reason="needs mypy")
@pytest.mark.parametrize("name", NAMES)
def test_example_type_checks_strictly(name, tmp_path):
    package = Path(PyLiite4.__file__).parent
    env = {"PATH": "/usr/bin:/bin"}
    # Strict for the example only: PyLiite4 from a source tree would otherwise be checked as part of it.
    config = tmp_path / "mypy.ini"
    config.write_text("[mypy]\nstrict = True\n\n[mypy-PyLiite4,PyLiite4.*]\nignore_errors = True\n")
    if package.parent.name != "site-packages":
        env["MYPYPATH"] = str(package.parent)
    result = subprocess.run([sys.executable, "-m", "mypy", "--config-file", str(config), "--no-error-summary",
                             "--cache-dir", str(tmp_path / "cache"), "."], cwd=EXAMPLES / name, capture_output=True,
                            text=True, env=env)
    assert result.returncode == 0, result.stdout[:3000] + result.stderr[:3000]
