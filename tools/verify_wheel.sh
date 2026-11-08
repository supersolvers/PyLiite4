#!/bin/bash
# Install a bundled wheel, and optionally the matching PyLiite4-Addons and PyLiite4-Poppler wheels,
# into a clean venv and run the test suite with the system's GTK stack hidden,
# so only the wheels' copies can satisfy it. The tests get their own D-Bus
# session, which starts no services, and no portals, so they can't reach the desktop.
#
# Usage: tools/verify_wheel.sh dist/pyliite4-*.whl [dist/pyliite4_addons-*.whl] [dist/pyliite4_poppler-*.whl]
set -euo pipefail
wheels=()
for wheel in "$@"; do wheels+=("$(realpath "$wheel")"); done
root=$(cd "$(dirname "$0")/.." && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
python3 -m venv "$work/venv"
"$work/venv/bin/pip" -q install "${wheels[@]}" pytest mypy
cp -r "$root/tests" "$root/examples" "$root/demos" "$work/"

libdir=/usr/lib/$(uname -m)-linux-gnu
hide=(--tmpfs /usr/lib/python3/dist-packages --tmpfs "$libdir/girepository-1.0" --tmpfs "$libdir/gdk-pixbuf-2.0"
      --tmpfs /usr/share/glib-2.0/schemas --tmpfs /usr/share/icons --tmpfs /usr/share/gir-1.0)
for library in libgtk-4.so.1 libadwaita-1.so.0 libgirepository-2.0.so.0 libglib-2.0.so.0 libgobject-2.0.so.0 \
               libgio-2.0.so.0 libpango-1.0.so.0 libcairo.so.2 libgdk_pixbuf-2.0.so.0 libwebkitgtk-6.0.so.4 \
               libjavascriptcoregtk-6.0.so.1 libvte-2.91-gtk4.so.0 libshumate-1.0.so.1 libspelling-1.so.2 \
               libgom-1.0.so.0 libmanette-0.2.so.0 libpoppler-glib.so.8; do
    if [ -e "$libdir/$library" ]; then hide+=(--ro-bind /dev/null "$libdir/$library"); fi
done
for library in "$libdir"/libpoppler.so.*; do
    if [ -e "$library" ]; then hide+=(--ro-bind /dev/null "$library"); fi
done

cat > "$work/maps.py" <<'PYTHON'
import re
from pathlib import Path

from PyLiite4 import Gtk, Adw

bundle = str(Path(Gtk.__file__).parent / "_bundled")
assert Gtk.get_major_version() == 4
libraries = {line.split()[-1] for line in open("/proc/self/maps") if ".so" in line}
outside = sorted(l for l in libraries if re.search(r"lib(gtk-4|adwaita|glib-2|gobject-2|gio-2|pango|cairo|girepository)", l)
                 and not l.startswith(bundle))
assert not outside, outside
import gi
assert gi.__file__.startswith(bundle), gi.__file__
print(f"all GTK libraries loaded from the wheel ({sum(l.startswith(bundle) for l in libraries)} files)")
PYTHON

isolated=(env -u WAYLAND_DISPLAY -u GI_TYPELIB_PATH -u XDG_DATA_DIRS GDK_BACKEND=x11 NO_AT_BRIDGE=1
          GDK_DEBUG=no-portals ADW_DISABLE_PORTAL=1 GSETTINGS_BACKEND=memory)
bus=(dbus-run-session --config-file="$work/tests/session-bus.conf" --)
# AppArmor restrictions on unprivileged bwrap can prevent a nested sandbox. Turn off WebKit's sandbox for this
# run and let glycin use its fallback. The next run checks both sandboxes outside the outer bwrap.
"${bus[@]}" xvfb-run -a bwrap --dev-bind / / "${hide[@]}" --chdir "$work" "${isolated[@]}" \
    PYLIITE4_KEEP_RENDER="${PYLIITE4_KEEP_RENDER:-}" WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS=1 \
    bash -c "'$work/venv/bin/python' -W ignore maps.py && '$work/venv/bin/python' -m pytest -q --no-header -p no:cacheprovider --tb=short -W ignore tests"

# Run outside the outer bwrap, with the system stack visible, to check GdkPixbuf image loading and both helper
# sandboxes. The add-on tests skip when their wheel isn't installed.
(cd "$work" && "${bus[@]}" xvfb-run -a "${isolated[@]}" \
    "$work/venv/bin/python" -m pytest -q --no-header -p no:cacheprovider --tb=short -W ignore tests/test_platform.py \
    tests/test_addons.py)
