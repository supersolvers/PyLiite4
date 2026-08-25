#!/usr/bin/env python3
"""Build a Linux wheel that contains GTK 4, libadwaita and PyGObject.

The libraries come from this machine or from --prefix, so the wheel runs only on
systems with the same architecture and at least the same glibc. See
tools/manylinux for building on an old distribution to reach more systems. Needs
patchelf.

Every bundled file must belong to a project whose license texts tools/third_party.py
can find, or the build fails. --sources collects those projects' source archives.

Usage: tools/build_wheel.py [--output DIR] [--no-icons] [--prefix DIR] [--sources DIR]
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

import third_party

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
# Bundled when the build has them; a wheel built from this machine's packages may not.
OPTIONAL_LIBRARIES = ["libgtksourceview-5.so.0", "libsoup-3.0.so.0", "libportal.so.1", "libportal-gtk4.so.1",
                      "libgstreamer-1.0.so.0", "libgstbase-1.0.so.0", "libgstaudio-1.0.so.0", "libgstvideo-1.0.so.0",
                      "libgstpbutils-1.0.so.0", "libgstapp-1.0.so.0"]
TYPELIBS = ["GLib-2.0", "GLibUnix-2.0", "GObject-2.0", "GModule-2.0", "Gio-2.0", "GioUnix-2.0", "GdkPixbuf-2.0",
            "Pango-1.0", "PangoCairo-1.0", "PangoFT2-1.0", "PangoFc-1.0", "PangoOT-1.0", "HarfBuzz-0.0", "cairo-1.0",
            "freetype2-2.0", "fontconfig-2.0", "Graphene-1.0", "Gdk-4.0", "GdkWayland-4.0", "GdkX11-4.0", "xlib-2.0",
            "Gsk-4.0", "Gtk-4.0", "Adw-1", "GtkSource-5", "Soup-3.0", "Xdp-1.0", "XdpGtk4-1.0", "Gst-1.0",
            "GstBase-1.0", "GstAudio-1.0", "GstVideo-1.0", "GstTag-1.0", "GstPbutils-1.0", "GstApp-1.0", "Rsvg-2.0"]
# Free formats and playback plumbing. Patent-encumbered codecs stay out of the wheel.
GSTREAMER_PLUGINS = ["app", "audioconvert", "audioresample", "autodetect", "coreelements", "gio", "isomp4", "matroska", "ogg",
                     "opengl", "opus", "playback", "pulseaudio", "audiofx", "theora", "typefindfunctions", "videoconvertscale",
                     "volume", "vorbis", "vpx", "wavparse"]
TRANSLATION_DOMAINS = ["gtk40", "gtk40-properties", "glib20", "gdk-pixbuf", "libadwaita", "gtksourceview-5",
                       "glib-networking", "libsoup-3.0", "libportal", "gstreamer-1.0", "gst-plugins-base-1.0"]
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


# Where each bundled file was copied from: {bundled path: source file}.
ORIGINS = {}
# Files the build writes itself rather than copying.
GENERATED = re.compile(r"(^|/)(loaders\.cache\.in|gschemas\.compiled|fonts\.conf)$")


def bring(source, target):
    """Copy a file into the bundle, to ``target`` or into the directory ``target``."""
    target = target / source.name if target.is_dir() else target
    shutil.copyfile(source, target)
    shutil.copymode(source, target)
    ORIGINS[target] = Path(source)
    return target


def copy_tree(source, target):
    for path in source.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts:
            (target / path.relative_to(source)).parent.mkdir(parents=True, exist_ok=True)
            bring(path, target / path.relative_to(source))


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
        bring(loader, loaders)
    tools = bundle / "bin"
    tools.mkdir()
    for tool in ("glib-compile-resources", "glib-compile-schemas"):
        bring(Path(shutil.which(tool)), tools)
    gio_modules = bundle / "lib" / "gio" / "modules"
    gio_modules.mkdir(parents=True)
    # TLS for GIO's network classes, which Soup uses for HTTPS.
    for module in ("libgioopenssl.so", "libgiognutls.so"):
        if (LIBDIR / "gio" / "modules" / module).exists():
            bring(LIBDIR / "gio" / "modules" / module, gio_modules)
            break

    # GdkPixbuf hands most image formats to these helper programs.
    glycin = []
    for version in [] if PREFIX else Path("/usr/libexec/glycin-loaders").glob("*"):
        target = bundle / "libexec" / "glycin-loaders" / version.name
        target.mkdir(parents=True)
        for program in version.iterdir():
            glycin.append(bring(program, target))
        configs = bundle / "share" / "glycin-loaders" / version.name / "conf.d"
        configs.mkdir(parents=True)
        for config in Path(f"/usr/share/glycin-loaders/{version.name}/conf.d").glob("*.conf"):
            text = config.read_text().replace("/usr/libexec/", "@BUNDLE@/libexec/")
            # Glycin's sandbox only shows loaders under /usr unless told otherwise.
            text = re.sub(r"^(Exec=.*)$", r"\1\nExposeBaseDir=true", text, flags=re.M)
            (configs / f"{config.name}.in").write_text(text)
            ORIGINS[configs / f"{config.name}.in"] = config

    im_modules = bundle / "lib" / "gtk-4.0" / "4.0.0" / "immodules"
    im_modules.mkdir(parents=True)
    for module in (LIBDIR / "gtk-4.0" / "4.0.0" / "immodules").glob("*.so"):
        bring(module, im_modules)

    plugins = bundle / "lib" / "gstreamer-1.0"
    plugins.mkdir()
    for plugin in GSTREAMER_PLUGINS:
        if (LIBDIR / "gstreamer-1.0" / f"libgst{plugin}.so").exists():
            bring(LIBDIR / "gstreamer-1.0" / f"libgst{plugin}.so", plugins)
        else:
            print(f"warning: GStreamer plugin {plugin} is not available", file=sys.stderr)
    (bundle / "libexec").mkdir(exist_ok=True)
    scanner = bundle / "libexec" / "gst-plugin-scanner"
    candidates = [*LIBDIR.glob("gstreamer1.0/gstreamer-1.0/gst-plugin-scanner"),
                  *LIBDIR.parent.glob("libexec/gstreamer-1.0/gst-plugin-scanner")]
    bring(candidates[0], scanner)

    launcher = LIBDIR.parent / "libexec" / "gio-launch-desktop"
    helpers = []
    if PREFIX and launcher.exists():
        helpers.append(bring(launcher, bundle / "libexec"))

    # Follow dependencies from every file that gets loaded.
    roots = ROOT_LIBRARIES + [name for name in OPTIONAL_LIBRARIES if (LIBDIR / name).exists()]
    for name in sorted(set(OPTIONAL_LIBRARIES) - set(roots)):
        print(f"warning: {name} is not available", file=sys.stderr)
    pending = [LIBDIR / name for name in roots]
    pending += python_extensions + list(loaders.glob("*.so")) + list(tools.iterdir()) + glycin
    pending += list(gio_modules.glob("*.so")) + list(im_modules.glob("*.so")) + list(plugins.glob("*.so")) + [scanner] + helpers
    copied = {}
    while pending:
        for name, source in ldd(pending.pop()).items():
            if name not in copied and not SYSTEM_LIBRARIES.match(name):
                copied[name] = source
                pending.append(source)
    for name in roots:
        copied.setdefault(name, LIBDIR / name)
    for name, source in copied.items():
        bring(source, lib / name)
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
    for module in gio_modules.glob("*.so"):
        set_runpath(module, "$ORIGIN/../..")
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
            bring(source, typelibs)
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
        bring(schema, schemas)
    subprocess.run(["glib-compile-schemas", str(schemas)], check=True)

    if PREFIX:
        for domain in TRANSLATION_DOMAINS:
            for catalog in (LIBDIR.parent / "share" / "locale").glob(f"*/LC_MESSAGES/{domain}.mo"):
                target = bundle / "share" / "locale" / catalog.relative_to(LIBDIR.parent / "share" / "locale")
                target.parent.mkdir(parents=True, exist_ok=True)
                bring(catalog, target)
        # Only used on systems without their own /etc/fonts/fonts.conf.
        fonts = bundle / "etc" / "fonts"
        fonts.mkdir(parents=True)
        (fonts / "fonts.conf").write_text(FALLBACK_FONTS_CONF)

    sourceview = LIBDIR.parent / "share" / "gtksourceview-5" if PREFIX else Path("/usr/share/gtksourceview-5")
    if sourceview.is_dir() and any(lib.glob("libgtksourceview-5.so*")):
        copy_tree(sourceview, bundle / "share" / "gtksourceview-5")

    if icons:
        copy_tree(Path("/usr/share/icons/Adwaita"), bundle / "share" / "icons" / "Adwaita")
        # hicolor is the fallback theme that applications install their own icons into; GTK needs only its index.
        (bundle / "share" / "icons" / "hicolor").mkdir()
        bring(Path("/usr/share/icons/hicolor/index.theme"), bundle / "share" / "icons" / "hicolor")

    return copied


def write_licenses(bundle, cache):
    """Attribute every bundled file to its project and write their notices. Returns the projects."""
    unrecorded = [str(path.relative_to(bundle)) for path in bundle.rglob("*")
                  if path.is_file() and path not in ORIGINS and not GENERATED.search(str(path))]
    if unrecorded:
        raise RuntimeError("bundled files without a recorded origin:\n  " + "\n  ".join(sorted(unrecorded)))
    origins = {str(path.relative_to(bundle)): source for path, source in ORIGINS.items()}
    components = third_party.Attribution(PREFIX, cache).attribute(origins)
    third_party.write_notices(components, bundle / "licenses")
    return components


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
    license_headers = "".join(f"License-File: {path}\n" for path in [*license_files, "THIRD-PARTY-NOTICES.txt"])
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
        f"{info}/licenses/THIRD-PARTY-NOTICES.txt": (package_dir / "_bundled" / "licenses" / "NOTICES.txt").read_text(),
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
    parser.add_argument("--sources", type=Path, help="copy the source archive of every bundled project here")
    parser.add_argument("--cache", type=Path, default=ROOT / "build" / "third-party",
                        help="where downloaded source packages are kept (default: build/third-party)")
    args = parser.parse_args()
    if args.prefix:
        global LIBDIR, PREFIX
        PREFIX = args.prefix
        LIBDIR = Path(args.prefix) / "lib"
    if args.sources and not args.prefix:
        parser.error("--sources needs --prefix: wheels built from this machine's packages aren't for release")
    if not shutil.which("patchelf"):
        parser.error("patchelf was not found")
    with tempfile.TemporaryDirectory() as directory:
        package = Path(directory) / "PyLiite4"
        shutil.copytree(ROOT / "src" / "PyLiite4", package, ignore=shutil.ignore_patterns("__pycache__", "_bundled"))
        if args.prefix:
            subprocess.run([sys.executable, ROOT / "tools" / "generate.py", "--gir-dir", f"{args.prefix}/share/gir-1.0",
                            "--output", package], check=True, stdout=subprocess.DEVNULL)
        libraries = build_bundle(package / "_bundled", not args.no_icons)
        components = write_licenses(package / "_bundled", args.cache.resolve())
        if args.sources:
            third_party.collect_sources(components, args.sources)
        # pycairo is private to the bundle, so PyLiite4.cairo carries its stubs.
        cairo_stubs = package / "_bundled" / "python" / "cairo" / "__init__.pyi"
        if cairo_stubs.exists():
            shutil.copy(cairo_stubs, package / "cairo.pyi")
        wheel = build_wheel(package, args.output)
    print(f"{wheel} ({wheel.stat().st_size / 1e6:.0f} MB, {len(libraries)} libraries)")


if __name__ == "__main__":
    main()
