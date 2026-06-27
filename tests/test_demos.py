"""Open every demo in demos/ and check that it runs without errors. See tests/run_demo.py."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from demos import gtk_demo, workbench  # noqa: E402

RUNNER = Path(__file__).with_name("run_demo.py")


def run(*arguments):
    result = subprocess.run([sys.executable, str(RUNNER), *arguments], capture_output=True, text=True, timeout=60,
                            env={**os.environ, "GSETTINGS_BACKEND": "memory", "GTK_A11Y": "none"})
    assert result.returncode == 0, result.stderr[-4000:]


@pytest.mark.parametrize("name", [demo.name for demo in gtk_demo.demos()])
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
