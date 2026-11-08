#!/usr/bin/env python3
"""Build the PyLiite4-Addons wheel (WebKitGTK, libshumate, libspelling, VTE, Gom, libmanette and glycin) or, with
--poppler, the PyLiite4-Poppler wheel.

The libraries come from --addons-prefix (tools/manylinux/build_addons.sh or build_poppler.sh), built on the stack in
--prefix. The wheel installs PyLiite4/_addons or PyLiite4/_poppler, whose libraries find the rest in the PyLiite4
wheel's PyLiite4/_bundled, so it bundles only what that wheel doesn't have. Build the PyLiite4 wheel into --output
first: this reads which libraries it has.

Poppler is GPL, so it has a wheel of its own, which an application that stays LGPL-compatible can leave out.

Usage: tools/build_addons_wheel.py --prefix /opt/gtk --addons-prefix /opt/addons [--poppler] [--output DIR]
           [--sources DIR]
"""

import argparse
import os
import xml.etree.ElementTree as ET
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

import build_wheel
import third_party
from build_wheel import ROOT, SYSTEM_LIBRARIES, bring, ldd, set_runpath


@dataclass
class Wheel:
    name: str
    summary: str
    bundle: str
    libraries: list
    typelibs: list
    translations: list
    license: str | None = None
    # The GPL projects it is for.
    gpl: tuple = ()


WHEELS = {
    "addons": Wheel("PyLiite4-Addons",
                    "WebKitGTK, libshumate, libspelling, VTE, Gom, libmanette and glycin for PyLiite4", "_addons",
                    ["libwebkitgtk-6.0.so.4", "libjavascriptcoregtk-6.0.so.1", "libshumate-1.0.so.1",
                     "libspelling-1.so.2", "libvte-2.91-gtk4.so.0", "libgom-1.0.so.0", "libmanette-0.2.so.0",
                     "libglycin-2.so.0", "libglycin-gtk4-2.so.0"],
                    ["JavaScriptCore-6.0", "WebKit-6.0", "Shumate-1.0", "Spelling-1", "Vte-3.91", "Gom-1.0",
                     "Manette-0.2", "Gly-2", "GlyGtk4-2"],
                    ["WebKitGTK-6.0", "vte-2.91", "shumate1", "libspelling"],
                    # glycin's JPEG XL loader compiles in jpegxl-rs and jpegxl-sys, which are GPL, so that program is.
                    # It's a separate process that glycin talks to over a socket, so it doesn't make applications GPL.
                    "LGPL-3.0-only AND GPL-3.0-or-later", ("jpegxl-rs", "jpegxl-sys")),
    # Its own generated module is PyLiite4's, under the LGPL; Poppler is GPL.
    "poppler": Wheel("PyLiite4-Poppler", "Poppler, for reading and drawing PDF documents, for PyLiite4 (GPL)",
                     "_poppler", ["libpoppler-glib.so.8"], ["Poppler-0.18"], [],
                     "LGPL-3.0-only AND (GPL-2.0-only OR GPL-3.0-only)", ("poppler",)),
}
# WebKit's own processes; its jsc shell isn't wanted.
WEBKIT_PROCESSES = ["WebKitWebProcess", "WebKitNetworkProcess", "WebKitGPUProcess"]
# From the bundle's directories, how to reach _bundled/lib next to them.
BUNDLED_LIB = "_bundled/lib"
TYPELIB_DIRS = ["{prefix}/lib/girepository-1.0", "{gtk}/lib/girepository-1.0", "/usr/lib64/girepository-1.0"]
GIR_DIRS = ["{prefix}/share/gir-1.0", "{gtk}/share/gir-1.0", "/usr/share/gir-1.0"]
CORE = "{http://www.gtk.org/introspection/core/1.0}"


def bundled_libraries(output):
    """The libraries the PyLiite4 wheel of this version, for this Python, already bundles."""
    version = build_wheel.tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    python = f"cp{sys.version_info.major}{sys.version_info.minor}"
    wheel = output / f"{build_wheel.distribution_name('PyLiite4')}-{version}-{python}-{python}-{build_wheel.glibc_tag()}.whl"
    if not wheel.exists():
        sys.exit(f"{wheel} is needed: build the PyLiite4 wheel first")
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
    libraries = {Path(name).name for name in names if name.startswith("PyLiite4/_bundled/lib/") and name.count("/") == 3}
    typelibs = {Path(name).stem for name in names if name.startswith("PyLiite4/_bundled/lib/girepository-1.0/")}
    return version, libraries, typelibs


def find(directories, name, prefix, gtk):
    return next(path for d in directories if (path := Path(d.format(prefix=prefix, gtk=gtk)) / name).exists())


def needed_typelibs(wheel, prefix, gtk, bundled):
    """The wheel's typelibs, and those they include that the PyLiite4 wheel lacks, such as libmanette's GUdev."""
    needed, pending = [], list(wheel.typelibs)
    while pending:
        name = pending.pop(0)
        if name in needed or name in bundled:
            continue
        needed.append(name)
        for include in ET.parse(find(GIR_DIRS, f"{name}.gir", prefix, gtk)).getroot().iter(f"{CORE}include"):
            pending.append(f"{include.get('name')}-{include.get('version')}")
    return [find(TYPELIB_DIRS, f"{name}.typelib", prefix, gtk) for name in needed]


def runpath(path, addons):
    """$ORIGIN-relative paths from path to the add-on bundle's lib and then the main bundle's."""
    up = os.path.relpath(addons / "lib", path.parent)
    bundled = os.path.relpath(addons.parent / BUNDLED_LIB, path.parent)
    return ":".join("$ORIGIN" if p == "." else f"$ORIGIN/{p}" for p in (up, bundled))


def build_addons(wheel, addons, prefix, gtk, bundled, bundled_typelibs):
    lib = addons / "lib"
    lib.mkdir(parents=True)
    helpers = []
    webkit = prefix / "lib" / "webkitgtk-6.0"
    if webkit.is_dir():
        (lib / "webkitgtk-6.0" / "injected-bundle").mkdir(parents=True)
        for process in WEBKIT_PROCESSES:
            helpers.append(bring(webkit / process, lib / "webkitgtk-6.0"))
        for module in (webkit / "injected-bundle").glob("*.so"):
            helpers.append(bring(module, lib / "webkitgtk-6.0" / "injected-bundle"))
        # The sandbox's D-Bus filter, which a patch lets WebKit find next to its processes.
        if (prefix / "bin" / "xdg-dbus-proxy").exists():
            helpers.append(bring(prefix / "bin" / "xdg-dbus-proxy", lib / "webkitgtk-6.0"))
    # Loader configs need absolute paths. Save templates here; fill in the installed paths at startup.
    for loaders in (prefix / "libexec" / "glycin-loaders").glob("*"):
        target = addons / "libexec" / "glycin-loaders" / loaders.name
        target.mkdir(parents=True)
        for loader in loaders.iterdir():
            helpers.append(bring(loader, target))
        configs = addons / "share" / "glycin-loaders" / loaders.name / "conf.d"
        configs.mkdir(parents=True)
        for config in (prefix / "share" / "glycin-loaders" / loaders.name / "conf.d").glob("*.conf"):
            template = configs / f"{config.name}.in"
            template.write_text(config.read_text().replace(f"{prefix}/", "@BUNDLE@/"))
            build_wheel.ORIGINS[template] = config
    # Enchant is built relocatable: it finds its providers and data next to its library.
    if (prefix / "lib" / "enchant-2").is_dir():
        (lib / "enchant-2").mkdir()
        for provider in (prefix / "lib" / "enchant-2").glob("*.so"):
            helpers.append(bring(provider, lib / "enchant-2"))
        (addons / "share" / "enchant-2").mkdir(parents=True)
        for data in (prefix / "share" / "enchant-2").iterdir():
            bring(data, addons / "share" / "enchant-2")

    # Follow dependencies, leaving out what the system or the PyLiite4 wheel provides.
    pending = [prefix / "lib" / name for name in wheel.libraries] + helpers
    copied = {}
    while pending:
        for name, source in ldd(pending.pop()).items():
            if name not in copied and name not in bundled and not SYSTEM_LIBRARIES.match(name):
                copied[name] = source
                pending.append(source)
    for name in wheel.libraries:
        copied.setdefault(name, prefix / "lib" / name)
    for name, source in copied.items():
        bring(source, lib / name)
    for path in [*(lib / name for name in copied), *helpers]:
        set_runpath(path, runpath(path, addons))

    # PyGObject overrides, such as Gom's, which PyGObject finds in any gi/overrides on sys.path.
    overrides = addons / "python" / "gi" / "overrides"
    for override in prefix.glob("lib/python3*/site-packages/gi/overrides/*.py"):
        overrides.mkdir(parents=True, exist_ok=True)
        bring(override, overrides)

    typelibs = lib / "girepository-1.0"
    typelibs.mkdir()
    for typelib in needed_typelibs(wheel, prefix, gtk, bundled_typelibs):
        bring(typelib, typelibs)
    for domain in wheel.translations:
        for catalog in (prefix / "share" / "locale").glob(f"*/LC_MESSAGES/{domain}.mo"):
            target = addons / "share" / "locale" / catalog.relative_to(prefix / "share" / "locale")
            target.parent.mkdir(parents=True, exist_ok=True)
            bring(catalog, target)
    return copied


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", required=True, help="the GTK stack the PyLiite4 wheel was built from")
    parser.add_argument("--addons-prefix", required=True, type=Path, help="where build_addons.sh or build_poppler.sh installed")
    parser.add_argument("--poppler", action="store_true", help="build PyLiite4-Poppler instead of PyLiite4-Addons")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--sources", type=Path, help="copy the source archive of every bundled project here")
    parser.add_argument("--cache", type=Path, default=ROOT / "build" / "third-party",
                        help="where downloaded source packages are kept (default: build/third-party)")
    args = parser.parse_args()
    build_wheel.PREFIX = args.prefix
    wheel = WHEELS["poppler" if args.poppler else "addons"]
    if not shutil.which("patchelf"):
        parser.error("patchelf was not found")
    version, bundled, bundled_typelibs = bundled_libraries(args.output)
    os.environ["LD_LIBRARY_PATH"] = f"{args.addons_prefix / 'lib'}:{os.environ.get('LD_LIBRARY_PATH', '')}"
    with tempfile.TemporaryDirectory() as directory:
        package = Path(directory) / "PyLiite4"
        package.mkdir()
        subprocess.run([sys.executable, ROOT / "tools" / "generate.py", "--poppler" if args.poppler else "--addons",
                        "--gir-dir",
                        f"{args.prefix}/share/gir-1.0", "--gir-dir", f"{args.addons_prefix}/share/gir-1.0",
                        "--output", package], check=True, stdout=subprocess.DEVNULL)
        bundle = package / wheel.bundle
        libraries = build_addons(wheel, bundle, args.addons_prefix, args.prefix, bundled, bundled_typelibs)
        components = build_wheel.write_licenses(bundle, args.cache.resolve(), [args.addons_prefix], wheel.gpl)
        if args.sources:
            third_party.collect_sources(components, args.sources)
        path = build_wheel.build_wheel(package, args.output, name=wheel.name, summary=wheel.summary,
                                       requires=[f"PyLiite4=={version}"], bundle=wheel.bundle, entry_points=False,
                                       license=wheel.license)
    print(f"{path} ({path.stat().st_size / 1e6:.0f} MB, {len(libraries)} libraries)")


if __name__ == "__main__":
    main()
