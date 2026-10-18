"""Point GTK and PyGObject at the libraries shipped inside a bundled wheel.

Wheels built by tools/build_wheel.py carry a ``_bundled`` directory. Source
checkouts and plain wheels don't, and use the system GTK instead. The
PyLiite4-Addons wheel adds an ``_addons`` directory, whose libraries link the
bundle's.
"""

import ctypes
import hashlib
import importlib
import os
import sys
import tempfile
from pathlib import Path

BUNDLE = Path(__file__).parent / "_bundled"
ADDONS = Path(__file__).parent / "_addons"
# Where distributions keep their combined CA certificates: Debian and its derivatives, Arch and Gentoo; Fedora and
# RHEL; openSUSE; Alpine.
CA_BUNDLES = ["/etc/ssl/certs/ca-certificates.crt", "/etc/pki/tls/certs/ca-bundle.crt", "/etc/ssl/ca-bundle.pem",
              "/etc/ssl/cert.pem"]


def _prepend(variable: str, value: Path, default: str = "") -> None:
    current = os.environ.get(variable, default)
    os.environ[variable] = f"{value}{os.pathsep}{current}" if current else str(value)


def _cache_directory() -> Path:
    name = hashlib.sha256(str(BUNDLE).encode()).hexdigest()[:16]
    cache_root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    for root in (cache_root / "PyLiite4", Path(tempfile.gettempdir()) / f"PyLiite4-{os.getuid()}"):
        try:
            (root / name).mkdir(parents=True, exist_ok=True)
            if os.access(root / name, os.W_OK):
                return root / name
        except OSError:
            continue
    raise OSError("no writable cache directory for PyLiite4")


def _write_config(relative_path: Path, template: Path) -> Path:
    """Instantiate a config file that must name absolute paths into the bundle.

    The install location may be read-only, so these go in a cache directory.
    Returns the directory that relative_path was created under.
    """
    text = template.read_text().replace("@BUNDLE@", str(BUNDLE))
    root = _cache_directory()
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text() != text:
        temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
        temporary.write_text(text)
        temporary.replace(path)
    return root


def bind_translations() -> None:
    """Point gettext at the bundled catalogs. GTK's own startup needs this repeated."""
    libc = ctypes.CDLL(None)
    libc.bindtextdomain.restype = ctypes.c_char_p
    libc.bindtextdomain.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    for locale in (BUNDLE / "share" / "locale", ADDONS / "share" / "locale"):
        domains = {catalog.stem for catalog in locale.glob("*/LC_MESSAGES/*.mo")}
        for domain in sorted(domains):
            libc.bindtextdomain(domain.encode(), str(locale).encode())


def setup() -> None:
    """Configure the process for the bundle, if this install has one."""
    if not BUNDLE.is_dir():
        return
    sys.path.insert(0, str(BUNDLE / "python"))
    _prepend("GI_TYPELIB_PATH", BUNDLE / "lib" / "girepository-1.0")
    _prepend("XDG_DATA_DIRS", BUNDLE / "share", "/usr/local/share:/usr/share")
    _prepend("PATH", BUNDLE / "bin")
    os.environ["GSETTINGS_SCHEMA_DIR"] = str(BUNDLE / "share" / "glib-2.0" / "schemas")
    # System GIO and GTK modules link the system's libraries, so keep them out.
    os.environ["GIO_MODULE_DIR"] = str(BUNDLE / "lib" / "gio" / "modules")
    os.environ["GTK_EXE_PREFIX"] = str(BUNDLE)
    os.environ["GTK_DATA_PREFIX"] = str(BUNDLE)
    # Wheels built from source have these paths compiled in as their build prefix.
    fallback_fonts = BUNDLE / "etc" / "fonts" / "fonts.conf"
    if fallback_fonts.exists() and not {"FONTCONFIG_FILE", "FONTCONFIG_PATH"} & set(os.environ):
        system_fonts = Path("/etc/fonts/fonts.conf")
        config = system_fonts if system_fonts.exists() else fallback_fonts
        os.environ["FONTCONFIG_FILE"] = str(config)
        # fonts.conf includes conf.d, where the family aliases such as "Sans" live, by a path relative to this.
        os.environ["FONTCONFIG_PATH"] = str(config.parent)
    # The bundled TLS module would look for certificates where the build machine keeps them.
    if any((BUNDLE / "lib" / "gio" / "modules").glob("libgioopenssl.so")) and "SSL_CERT_FILE" not in os.environ:
        for certificates in CA_BUNDLES:
            if Path(certificates).exists():
                os.environ["SSL_CERT_FILE"] = certificates
                break
    launcher = BUNDLE / "libexec" / "gio-launch-desktop"
    if launcher.exists():
        os.environ["GIO_LAUNCH_DESKTOP"] = str(launcher)
    bind_translations()

    gstreamer = BUNDLE / "lib" / "gstreamer-1.0"
    if gstreamer.is_dir():
        os.environ["GST_PLUGIN_SYSTEM_PATH_1_0"] = str(gstreamer)
        os.environ["GST_PLUGIN_SCANNER_1_0"] = str(BUNDLE / "libexec" / "gst-plugin-scanner")
        # GStreamer would otherwise share and keep rewriting the system's plugin registry.
        os.environ["GST_REGISTRY_1_0"] = str(_cache_directory() / "gstreamer-registry.bin")

    pixbuf_template = BUNDLE / "lib" / "gdk-pixbuf" / "loaders.cache.in"
    if pixbuf_template.exists():
        relative = Path("gdk-pixbuf") / "loaders.cache"
        os.environ["GDK_PIXBUF_MODULE_FILE"] = str(_write_config(relative, pixbuf_template) / relative)
    for template in (BUNDLE / "share" / "glycin-loaders").glob("*/conf.d/*.conf.in"):
        relative = Path("glycin") / "glycin-loaders" / template.relative_to(BUNDLE / "share" / "glycin-loaders").with_suffix("")
        os.environ["GLYCIN_DATA_DIR"] = str(_write_config(relative, template) / "glycin")
    if ADDONS.is_dir():
        _setup_addons()


def _setup_addons() -> None:
    _prepend("GI_TYPELIB_PATH", ADDONS / "lib" / "girepository-1.0")
    # The add-ons' PyGObject overrides, in a gi/overrides that PyGObject adds to its own.
    sys.path.insert(1, str(ADDONS / "python"))
    # WebKit's helper processes, which a patch lets it find here.
    webkit = ADDONS / "lib" / "webkitgtk-6.0"
    if webkit.is_dir():
        os.environ["WEBKIT_EXEC_PATH"] = str(webkit)
        os.environ["WEBKIT_INJECTED_BUNDLE_PATH"] = str(webkit / "injected-bundle")
    # GObject Introspection loads a namespace's library by name, which finds only the bundle's own.
    repository = importlib.import_module("gi._gi").Repository.get_default()
    repository.prepend_library_path(str(ADDONS / "lib"))
