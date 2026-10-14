"""pyliite4-deploy: freeze the example application with PyInstaller and run the result."""

import importlib.util
import os
import shutil
import signal
import subprocess
from pathlib import Path

import pytest

from PyLiite4.tools import deploy

EXAMPLE = Path(__file__).parent.parent / "examples" / "hello.py"

# Runs inside the frozen app before its script: once the window is up, report what loaded it, then quit.
PROBE = """
import os, sys
from PyLiite4 import Gio, GLib, Gtk

def probe():
    app = Gio.Application.get_default()
    windows = app.get_windows() if app else []
    if not windows or not windows[0].get_mapped():
        return True
    import gi
    bundle = os.path.join(sys._MEIPASS, "PyLiite4", "_bundled")
    gtk = [l.split()[-1] for l in open("/proc/self/maps") if "libgtk-4" in l]
    with open(os.environ["PROBE_REPORT"], "w") as report:
        from_bundle = bool(gtk) and all(path.startswith(bundle) for path in gtk)
        print(windows[0].get_title(), gi.__file__.startswith(bundle), from_bundle, file=report)
    app.quit()
    return False

GLib.timeout_add(100, probe)
"""


def test_deploy_needs_pyinstaller(monkeypatch, capsys, tmp_path):
    real_find_spec = importlib.util.find_spec
    monkeypatch.setattr(importlib.util, "find_spec",
                        lambda name, *args: None if name == "PyInstaller" else real_find_spec(name, *args))
    assert deploy.main([str(EXAMPLE), "-o", str(tmp_path)]) == 1
    assert "PyInstaller is not installed" in capsys.readouterr().err


@pytest.mark.skipif(importlib.util.find_spec("PyInstaller") is None, reason="PyInstaller is not installed")
@pytest.mark.skipif(not deploy.BUNDLE.is_dir(), reason="needs PyLiite4 installed from a bundled wheel")
def test_deploy_freezes_and_runs_the_example(tmp_path, monkeypatch):
    if not os.environ.get("DISPLAY"):
        pytest.skip("no X display: run the tests under xvfb-run")
    monkeypatch.chdir(tmp_path)
    (tmp_path / "probe.py").write_text(PROBE)
    assert deploy.main([str(EXAMPLE), "--name", "hello-app", "--", "--runtime-hook", str(tmp_path / "probe.py"),
                        "--log-level", "WARN"]) == 0
    binary = tmp_path / "dist" / "hello-app" / "hello-app"
    assert binary.is_file()
    assert (binary.parent / "_internal" / "PyLiite4" / "_bundled" / "lib" / "libgtk-4.so.1").exists()

    # A clean environment, away from the desktop session, so nothing PyLiite4 set up in this process leaks in.
    report = tmp_path / "report.txt"
    env = {"HOME": str(tmp_path), "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "DISPLAY": os.environ["DISPLAY"],
           "GDK_BACKEND": "x11", "GDK_DEBUG": "no-portals", "ADW_DISABLE_PORTAL": "1", "GTK_A11Y": "none",
           "NO_AT_BRIDGE": "1", "GSETTINGS_BACKEND": "memory", "PROBE_REPORT": str(report)}
    if "XAUTHORITY" in os.environ:
        env["XAUTHORITY"] = os.environ["XAUTHORITY"]
    command = [str(binary)]
    if shutil.which("dbus-run-session"):
        command = ["dbus-run-session", "--", *command]
    with open(tmp_path / "output.log", "w") as output:
        process = subprocess.Popen(command, env=env, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            status = process.wait(timeout=60)
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    assert status == 0, (tmp_path / "output.log").read_text()
    assert report.read_text().split() == ["PyLiite4", "True", "True"]
