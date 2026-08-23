"""Open every demo in demos/ and check that it runs without errors. See tests/run_demo.py."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from demos import gtk_demo, workbench  # noqa: E402

RUNNER = Path(__file__).with_name("run_demo.py")


def run(*arguments):
    # A private bus with portals off: demos must not reach the desktop's portals or other services.
    command = [sys.executable, str(RUNNER), *arguments]
    if shutil.which("dbus-run-session"):
        command = ["dbus-run-session", "--", *command]
    env = {**os.environ, "GSETTINGS_BACKEND": "memory", "GTK_A11Y": "none", "GDK_DEBUG": "no-portals",
           "ADW_DISABLE_PORTAL": "1"}
    # GDK prefers Wayland, so under xvfb-run an inherited WAYLAND_DISPLAY would put windows on the real desktop.
    # GDK also finds wayland-0 by itself, so name the backend too.
    if env.get("GDK_BACKEND") != "wayland":
        env.pop("WAYLAND_DISPLAY", None)
        env["GDK_BACKEND"] = "x11"
    result = subprocess.run(command, capture_output=True, text=True, timeout=60, env=env)
    assert result.returncode == 0, result.stderr[-4000:]


# Demos that crash outside the port, with the reason.
KNOWN_CRASHES = {
    # Playing video through GStreamer's GL upload while GDK has GL segfaults in the GL thread, with the system's GTK
    # 4.22 and GStreamer as well as the bundled ones, under Mesa and NVIDIA alike. GDK_DISABLE=gl avoids it.
    "sliding_puzzle": "GTK and GStreamer GL video crash, see KNOWN_CRASHES",
}


@pytest.mark.parametrize("name", [pytest.param(demo.name, marks=pytest.mark.xfail(reason=KNOWN_CRASHES[demo.name]))
                                  if demo.name in KNOWN_CRASHES else demo.name for demo in gtk_demo.all_demos()])
def test_gtk_demo(name):
    run("gtk_demo", name)


@pytest.mark.parametrize("demo", workbench.demos(), ids=lambda demo: demo.name)
def test_workbench_demo(demo):
    if demo.missing:
        pytest.skip(f"needs {', '.join(demo.missing)}")
    run("workbench", demo.name)


@pytest.mark.skipif(not (ROOT / "demos" / "adwaita_demo" / "__init__.py").exists(), reason="not ported yet")
def test_adwaita_demo():
    run("adwaita_demo")
