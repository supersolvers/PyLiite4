"""Collect a PyLiite4 wheel's ``_bundled`` tree: GTK and its libraries, typelibs, data and PyGObject.

The bundled PyGObject lives outside the normal import path, in ``_bundled/python``, and ``_bundle.setup()`` adds it
to ``sys.path`` at import. PyInstaller's analysis can't see it, so this hook copies it as files and names the
standard library modules it imports as hidden imports. A PyGObject installed in the build environment would shadow
it, so it is kept out of the freeze.
"""

import ast
import importlib.util
import sys
from pathlib import Path

spec = importlib.util.find_spec("PyLiite4")
package = Path(next(iter(spec.submodule_search_locations)))
bundle = package / "_bundled"

datas = []
hiddenimports = []
excludedimports = ["gi", "cairo"]
# Some of these, such as collections.abc, live in base_library.zip, where the check for hidden imports misses them.
warn_on_missing_hiddenimports = False

if bundle.is_dir():
    stdlib = set(sys.stdlib_module_names)
    imported = set()
    for path in sorted(bundle.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        datas.append((str(path), str(Path("PyLiite4") / path.parent.relative_to(package))))
        if path.suffix == ".py" and "python" == path.relative_to(bundle).parts[0]:
            for node in ast.walk(ast.parse(path.read_bytes(), str(path))):
                if isinstance(node, ast.Import):
                    imported.update(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                    imported.add(node.module)
    hiddenimports = sorted(name for name in imported if name.split(".")[0] in stdlib)
