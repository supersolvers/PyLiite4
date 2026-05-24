#!/usr/bin/env python3
"""Build a Linux wheel that contains GTK 4, libadwaita and PyGObject.

The libraries come from this machine or from --prefix, so the wheel runs only on
systems with the same architecture and at least the same glibc. See
tools/manylinux for building on an old distribution to reach more systems. Needs
patchelf.

Usage: tools/build_wheel.py [--output DIR] [--no-icons] [--prefix DIR]
"""

import argparse
import base64
import hashlib
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

try:
    import tomllib
except ImportError:  # Python 3.10
    import tomli as tomllib

PREFIX = None
ROOT = Path(__file__).resolve().parent.parent
# Replaced by --prefix: the directory holding GTK's libraries and their plugins.
LIBDIR = Path(f"/usr/lib/{platform.machine()}-linux-gnu")

ROOT_LIBRARIES = ["libgtk-4.so.1", "libadwaita-1.so.0", "libgirepository-2.0.so.0", "libgraphene-1.0.so.0",
                  "libgdk_pixbuf-2.0.so.0", "libpangocairo-1.0.so.0", "libpangoft2-1.0.so.0",
                  "libcairo-gobject.so.2", "libgmodule-2.0.so.0", "libharfbuzz.so.0", "libharfbuzz-gobject.so.0"]
TYPELIBS = ["GLib-2.0", "GLibUnix-2.0", "GObject-2.0", "GModule-2.0", "Gio-2.0", "GioUnix-2.0", "GdkPixbuf-2.0",
            "Pango-1.0", "PangoCairo-1.0", "PangoFT2-1.0", "PangoFc-1.0", "PangoOT-1.0", "HarfBuzz-0.0", "cairo-1.0",
            "freetype2-2.0", "fontconfig-2.0", "Graphene-1.0", "Gdk-4.0", "GdkWayland-4.0", "GdkX11-4.0", "xlib-2.0",
            "Gsk-4.0", "Gtk-4.0", "Adw-1"]
# Free formats and playback plumbing. Patent-encumbered codecs stay out of the wheel.
GSTREAMER_PLUGINS = ["app", "audioconvert", "audioresample", "autodetect", "coreelements", "gio", "isomp4", "matroska", "ogg",
                     "opengl", "opus", "playback", "pulseaudio", "audiofx", "theora", "typefindfunctions", "videoconvertscale",
                     "volume", "vorbis", "vpx", "wavparse"]
TRANSLATION_DOMAINS = ["gtk40", "gtk40-properties", "glib20", "gdk-pixbuf", "libadwaita"]
FALLBACK_FONTS_CONF = """<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
<fontconfig>
  <dir>/usr/share/fonts</dir>
  <dir>/usr/local/share/fonts</dir>
  <dir prefix="xdg">fonts</dir>
  <cachedir prefix="xdg">fontconfig</cachedir>
</fontconfig>
"""
# Provided by every system, or tied to its kernel and graphics drivers.
SYSTEM_LIBRARIES = re.compile(
    r"^(linux-vdso|ld-linux|libc|libm|libdl|librt|libpthread|libutil|libresolv|libnsl|libgcc_s|libstdc\+\+|libGL|"
    r"libEGL|libGLX|libGLdispatch|libOpenGL|libvulkan|libdrm|libgbm)\.so")


def ldd(path):
    output = subprocess.run(["ldd", str(path)], capture_output=True, text=True, check=True).stdout
    found = {}
    for line in output.splitlines():
        match = re.match(r"\s*(\S+) => (\S+)", line)
        if match and match[2] != "not":
            found[match[1]] = Path(match[2])
        elif match:
            raise RuntimeError(f"{path}: {line.strip()}")
    return found


def set_runpath(path, runpath):
    path.chmod(path.stat().st_mode | 0o200)
    subprocess.run(["patchelf", "--set-rpath", runpath, str(path)], check=True)


def copy_tree(source, target):
    shutil.copytree(source, target, symlinks=False, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__"))


def write_licenses(libraries, bundle):
    """Copy the copyright file of each Debian package we took a library from."""
    target = bundle / "licenses"
    target.mkdir()
    if shutil.which("dpkg-query"):
        packages = set()
        for library in libraries:
            result = subprocess.run(["dpkg-query", "-S", str(library)], capture_output=True, text=True)
            if result.returncode:
                result = subprocess.run(["dpkg-query", "-S", str(library).removeprefix("/usr")],
                                        capture_output=True, text=True)
            if result.returncode == 0:
                packages.add(result.stdout.split(":")[0])
        for package in packages:
            copyright_file = Path("/usr/share/doc") / package / "copyright"
            if copyright_file.exists():
                shutil.copy(copyright_file, target / f"{package}.txt")
    if shutil.which("rpm"):
        for library in libraries:
            result = subprocess.run(["rpm", "-qf", "--qf", "%{NAME}", str(library)], capture_output=True, text=True)
            licenses = Path("/usr/share/licenses") / result.stdout
            if result.returncode == 0 and licenses.is_dir():
                copy_tree(licenses, target / result.stdout)
    # Packages built from source keep their license files in the source tree.
    for source in Path("/src").glob("*/"):
        if source.name.startswith("build-") or source.name in ("archives", "stamps"):
            continue
        for license_file in [*source.glob("COPYING*"), *source.glob("LICENSE*")]:
            if license_file.is_file():
                (target / source.name).mkdir(exist_ok=True)
                shutil.copy(license_file, target / source.name)


def build_bundle(bundle, icons):
    lib = bundle / "lib"
    lib.mkdir(parents=True)

    import gi
    python_source = Path(gi.__file__).parent
    python_target = bundle / "python"
    copy_tree(python_source, python_target / "gi")
    try:
        import cairo
        copy_tree(Path(cairo.__file__).parent, python_target / "cairo")
    except ImportError:
        pass
    python_extensions = list(python_target.rglob("*.so"))

    pixbuf_root = next(LIBDIR.glob("gdk-pixbuf-2.0/*/"))
    pixbuf_tools = [*LIBDIR.glob("gdk-pixbuf-2.0/gdk-pixbuf-query-loaders"), LIBDIR.parent / "bin" / "gdk-pixbuf-query-loaders"]
    loaders = bundle / "lib" / "gdk-pixbuf" / "loaders"
    loaders.mkdir(parents=True)
    for loader in (pixbuf_root / "loaders").glob("*.so"):
        shutil.copy(loader, loaders)
    tools = bundle / "bin"
    tools.mkdir()
    for tool in ("glib-compile-resources", "glib-compile-schemas"):
        shutil.copy(shutil.which(tool), tools)
    (bundle / "lib" / "gio" / "modules").mkdir(parents=True)

    # GdkPixbuf hands most image formats to these helper programs.
    glycin = []
    for version in [*Path("/usr/libexec/glycin-loaders").glob("*")] if LIBDIR.parent != Path(PREFIX) else []:
        target = bundle / "libexec" / "glycin-loaders" / version.name
        target.mkdir(parents=True)
        for program in version.iterdir():
            shutil.copy(program, target)
            glycin.append(target / program.name)
        configs = bundle / "share" / "glycin-loaders" / version.name / "conf.d"
        configs.mkdir(parents=True)
        for config in Path(f"/usr/share/glycin-loaders/{version.name}/conf.d").glob("*.conf"):
            text = config.read_text().replace("/usr/libexec/", "@BUNDLE@/libexec/")
            # Glycin's sandbox only shows loaders under /usr unless told otherwise.
            text = re.sub(r"^(Exec=.*)$", r"\1\nExposeBaseDir=true", text, flags=re.M)
            (configs / f"{config.name}.in").write_text(text)

    im_modules = bundle / "lib" / "gtk-4.0" / "4.0.0" / "immodules"
    im_modules.mkdir(parents=True)
    for module in (LIBDIR / "gtk-4.0" / "4.0.0" / "immodules").glob("*.so"):
        shutil.copy(module, im_modules)

    plugins = bundle / "lib" / "gstreamer-1.0"
    plugins.mkdir()
    for plugin in GSTREAMER_PLUGINS:
        if (LIBDIR / "gstreamer-1.0" / f"libgst{plugin}.so").exists():
            shutil.copy(LIBDIR / "gstreamer-1.0" / f"libgst{plugin}.so", plugins)
        else:
            print(f"warning: GStreamer plugin {plugin} is not available", file=sys.stderr)
    (bundle / "libexec").mkdir(exist_ok=True)
    scanner = bundle / "libexec" / "gst-plugin-scanner"
    candidates = [*LIBDIR.glob("gstreamer1.0/gstreamer-1.0/gst-plugin-scanner"),
                  *LIBDIR.parent.glob("libexec/gstreamer-1.0/gst-plugin-scanner")]
    shutil.copy(candidates[0], scanner)

    launcher = LIBDIR.parent / "libexec" / "gio-launch-desktop"
    helpers = []
    if PREFIX and launcher.exists():
        shutil.copy(launcher, bundle / "libexec")
        helpers.append(bundle / "libexec" / launcher.name)

    # Follow dependencies from every file that gets loaded.
    pending = [LIBDIR / name for name in ROOT_LIBRARIES]
    pending += python_extensions + list(loaders.glob("*.so")) + list(tools.iterdir()) + glycin
    pending += list(im_modules.glob("*.so")) + list(plugins.glob("*.so")) + [scanner] + helpers
    copied = {}
    while pending:
        for name, source in ldd(pending.pop()).items():
            if name not in copied and not SYSTEM_LIBRARIES.match(name):
                copied[name] = source
                pending.append(source)
    for name in ROOT_LIBRARIES:
        copied.setdefault(name, LIBDIR / name)
    for name, source in copied.items():
        shutil.copyfile(source, lib / name)
        set_runpath(lib / name, "$ORIGIN")
    for extension in python_extensions:
        depth = "/".join([".."] * len(extension.relative_to(bundle).parts[:-1]))
        set_runpath(extension, f"$ORIGIN/{depth}/lib")
    for loader in loaders.glob("*.so"):
        set_runpath(loader, "$ORIGIN/../..")
    for tool in tools.iterdir():
        set_runpath(tool, "$ORIGIN/../lib")
    for program in glycin:
        set_runpath(program, "$ORIGIN/../../../lib")
    for module in im_modules.glob("*.so"):
        set_runpath(module, "$ORIGIN/../../..")
    for plugin in plugins.glob("*.so"):
        set_runpath(plugin, "$ORIGIN/..")
    set_runpath(scanner, "$ORIGIN/../lib")
    for helper in helpers:
        set_runpath(helper, "$ORIGIN/../lib")

    typelibs = lib / "girepository-1.0"
    typelibs.mkdir()
    for name in TYPELIBS:
        source = LIBDIR / "girepository-1.0" / f"{name}.typelib"
        if source.exists():
            shutil.copy(source, typelibs)
        else:
            print(f"warning: typelib {name} is not available", file=sys.stderr)

    if any(loaders.glob("*.so")):
        query = next(tool for tool in pixbuf_tools if tool.exists())
        output = subprocess.run([query, *map(str, loaders.glob("*.so"))], capture_output=True, text=True, check=True).stdout
        cache = "\n".join(line for line in output.splitlines() if not line.startswith("#"))
        (loaders.parent / "loaders.cache.in").write_text(cache.replace(str(bundle), "@BUNDLE@") + "\n")

    schemas = bundle / "share" / "glib-2.0" / "schemas"
    schemas.mkdir(parents=True)
    for schema in (LIBDIR.parent / "share" / "glib-2.0" / "schemas" if PREFIX == str(LIBDIR.parent)
                   else Path("/usr/share/glib-2.0/schemas")).glob("org.gtk.*.gschema.xml"):
        shutil.copy(schema, schemas)
    subprocess.run(["glib-compile-schemas", str(schemas)], check=True)

    if PREFIX:
        for domain in TRANSLATION_DOMAINS:
            for catalog in (LIBDIR.parent / "share" / "locale").glob(f"*/LC_MESSAGES/{domain}.mo"):
                target = bundle / "share" / "locale" / catalog.relative_to(LIBDIR.parent / "share" / "locale")
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(catalog, target)
        # Only used on systems without their own /etc/fonts/fonts.conf.
        fonts = bundle / "etc" / "fonts"
        fonts.mkdir(parents=True)
        (fonts / "fonts.conf").write_text(FALLBACK_FONTS_CONF)

    if icons:
        for theme in ("Adwaita", "hicolor"):
            if Path(f"/usr/share/icons/{theme}").exists():
                copy_tree(Path(f"/usr/share/icons/{theme}"), bundle / "share" / "icons" / theme)

    write_licenses([*copied.values(), *python_extensions], bundle)
    return copied


def glibc_tag():
    major, minor = platform.libc_ver()[1].split(".")[:2]
    return f"manylinux_{major}_{minor}_{platform.machine()}"


def build_wheel(package_dir, output):
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    name, version = project["name"], project["version"]
    python = f"cp{sys.version_info.major}{sys.version_info.minor}"
    tag = f"{python}-{python}-{glibc_tag()}"
    info = f"{name}-{version}.dist-info"
    license_files = {path: (ROOT / path).read_text() for path in project["license-files"]}
    license_headers = "".join(f"License-File: {path}\n" for path in license_files)
    metadata = (f"Metadata-Version: 2.4\nName: {name}\nVersion: {version}\nSummary: {project['description']}\n"
                f"License-Expression: {project['license']}\n{license_headers}"
                f"Requires-Python: =={sys.version_info.major}.{sys.version_info.minor}.*\n"
                f"Description-Content-Type: text/markdown\n\n{(ROOT / 'README.md').read_text()}")
    scripts = "\n".join(f"{k} = {v}" for k, v in project["scripts"].items())
    extra = {
        f"{info}/METADATA": metadata,
        f"{info}/WHEEL": f"Wheel-Version: 1.0\nGenerator: PyLiite4 build_wheel\nRoot-Is-Purelib: false\nTag: {tag}\n",
        f"{info}/entry_points.txt": f"[console_scripts]\n{scripts}\n",
        **{f"{info}/licenses/{path}": text for path, text in license_files.items()},
    }
    output.mkdir(parents=True, exist_ok=True)
    wheel = output / f"{name}-{version}-{tag}.whl"
    record = []
    with zipfile.ZipFile(wheel, "w", zipfile.ZIP_DEFLATED) as archive:
        def add(arcname, data, mode=0o644):
            entry = zipfile.ZipInfo(arcname, date_time=(2026, 1, 1, 0, 0, 0))
            entry.external_attr = (mode | 0o100000) << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, data)
            digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
            record.append(f"{arcname},sha256={digest},{len(data)}")

        for path in sorted(package_dir.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                add(f"PyLiite4/{path.relative_to(package_dir)}", path.read_bytes(),
                    0o755 if path.stat().st_mode & 0o111 else 0o644)
        for arcname, text in extra.items():
            add(arcname, text.encode())
        archive.writestr(f"{info}/RECORD", "\n".join(record + [f"{info}/RECORD,,"]) + "\n")
    return wheel


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--no-icons", action="store_true")
    parser.add_argument("--prefix", help="use a GTK stack installed here, generating stubs from it")
    args = parser.parse_args()
    if args.prefix:
        global LIBDIR, PREFIX
        PREFIX = args.prefix
        LIBDIR = Path(args.prefix) / "lib"
    if not shutil.which("patchelf"):
        parser.error("patchelf was not found")
    with tempfile.TemporaryDirectory() as directory:
        package = Path(directory) / "PyLiite4"
        shutil.copytree(ROOT / "src" / "PyLiite4", package, ignore=shutil.ignore_patterns("__pycache__", "_bundled"))
        if args.prefix:
            subprocess.run([sys.executable, ROOT / "tools" / "generate.py", "--gir-dir", f"{args.prefix}/share/gir-1.0",
                            "--output", package], check=True, stdout=subprocess.DEVNULL)
        libraries = build_bundle(package / "_bundled", not args.no_icons)
        # pycairo is private to the bundle, so PyLiite4.cairo carries its stubs.
        cairo_stubs = package / "_bundled" / "python" / "cairo" / "__init__.pyi"
        if cairo_stubs.exists():
            shutil.copy(cairo_stubs, package / "cairo.pyi")
        wheel = build_wheel(package, args.output)
    print(f"{wheel} ({wheel.stat().st_size / 1e6:.0f} MB, {len(libraries)} libraries)")


if __name__ == "__main__":
    main()
