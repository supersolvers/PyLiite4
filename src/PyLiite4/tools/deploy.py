"""Freeze a PyLiite4 application into a folder that runs without Python, using PyInstaller.

The result is one folder, dist/NAME, holding the executable NAME and an _internal directory with Python, the
application's modules and the GTK stack from PyLiite4's bundled wheel. Copy or archive the whole folder; the
executable doesn't work on its own. Python itself comes from the build machine, so the app needs a glibc at least
as new as the build machine's, as well as the 2.34 the wheel needs: build on the oldest system you support.

This needs PyInstaller (pip install pyinstaller) and PyLiite4 installed from a bundled manylinux wheel. Ship data
files as GResources (see pyliite4-resources) so they are part of the Python code, or name them with --add-data.
Arguments after -- go to PyInstaller unchanged, as in: pyliite4-deploy app.py -- --add-data data:data.
PyInstaller also writes NAME.spec to the current directory, and pyinstaller NAME.spec rebuilds from it.
"""

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

BUNDLE = Path(__file__).resolve().parent.parent / "_bundled"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pyliite4-deploy", usage="%(prog)s [options] script [-- pyinstaller options]",
                                     description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("script", type=Path, help="the application's main script")
    parser.add_argument("-n", "--name", help="name of the application and its executable (default: the script's name)")
    parser.add_argument("-o", "--dist", type=Path, default=Path("dist"), help="where to put the app (default: dist)")
    parser.add_argument("--work", type=Path, default=Path("build"),
                        help="directory for PyInstaller's intermediate files (default: build)")
    argv = sys.argv[1:] if argv is None else argv
    split = argv.index("--") if "--" in argv else len(argv)
    args, pyinstaller_args = parser.parse_args(argv[:split]), argv[split + 1:]

    if importlib.util.find_spec("PyInstaller") is None:
        print("pyliite4-deploy: PyInstaller is not installed. Install it with: pip install pyinstaller",
              file=sys.stderr)
        return 1
    if not BUNDLE.is_dir():
        print("pyliite4-deploy: this PyLiite4 has no bundled GTK, so there is nothing to ship with the app. "
              "Install PyLiite4 from a manylinux wheel.", file=sys.stderr)
        return 1
    if not args.script.is_file():
        print(f"pyliite4-deploy: {args.script} does not exist", file=sys.stderr)
        return 1

    name = args.name or args.script.stem
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--onedir", "--name", name,
               "--distpath", str(args.dist), "--workpath", str(args.work),
               # PyLiite4 loads its own copy of PyGObject. One installed beside it must not be frozen in its place.
               "--exclude-module", "gi", "--exclude-module", "cairo",
               *pyinstaller_args, str(args.script.resolve())]
    result = subprocess.run(command)
    if result.returncode:
        return result.returncode
    print(f"pyliite4-deploy: built {args.dist / name / name}. Ship the whole {args.dist / name} folder.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
