"""PyInstaller support. PyInstaller finds this through the ``pyinstaller40`` entry point."""

from pathlib import Path


def get_hook_dirs() -> list[str]:
    return [str(Path(__file__).parent)]
