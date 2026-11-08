#!/bin/bash
# Like verify_wheel.sh, but on Wayland: install a bundled wheel into a clean venv and run the tests on a headless
# KWin compositor, with the system's GTK stack hidden. Run it in its own D-Bus session, so the headless KWin
# stays apart from the desktop's.
#
# Usage: dbus-run-session --config-file=tests/session-bus.conf -- tools/verify_wayland.sh dist/pyliite4-*.whl
set -euo pipefail
wheel=$(realpath "$1"); project=$(cd "$(dirname "$0")/.." && pwd)
if [ "${DBUS_SESSION_BUS_ADDRESS:-}" = "unix:path=$XDG_RUNTIME_DIR/bus" ]; then
    echo "run this under dbus-run-session, not on the desktop's session bus" >&2; exit 1
fi
work=$(mktemp -d)
cleanup() {
    # KWin starts portals and other services on this bus, which outlive it unless stopped here.
    for pid in $(pgrep -u "$(id -u)"); do
        if [ "$pid" != $$ ] && [ "$pid" != "$PPID" ] && tr '\0' '\n' < "/proc/$pid/environ" 2>/dev/null \
            | grep -qxF "DBUS_SESSION_BUS_ADDRESS=$DBUS_SESSION_BUS_ADDRESS"; then
            kill "$pid" 2>/dev/null || true
        fi
    done
    rm -rf "$work"
}
trap cleanup EXIT
python3 -m venv "$work/venv"; "$work/venv/bin/pip" -q install "$wheel" pytest mypy
cp -r "$project/tests" "$project/examples" "$project/demos" "$work/"
socket=pyliite4-wl-$$
env -u DISPLAY -u WAYLAND_DISPLAY kwin_wayland --virtual --width 1024 --height 768 --socket "$socket" >"$work/kwin.log" 2>&1 &
kwin=$!
for _ in $(seq 50); do [ -S "$XDG_RUNTIME_DIR/$socket" ] && break; sleep 0.2; done
[ -S "$XDG_RUNTIME_DIR/$socket" ] || { cat "$work/kwin.log"; exit 1; }
libdir=/usr/lib/$(uname -m)-linux-gnu
hide=(--tmpfs /usr/lib/python3/dist-packages --tmpfs "$libdir/girepository-1.0" --tmpfs "$libdir/gdk-pixbuf-2.0"
      --tmpfs /usr/share/glib-2.0/schemas --tmpfs /usr/share/icons --tmpfs /usr/share/gir-1.0)
for library in libgtk-4.so.1 libadwaita-1.so.0 libgirepository-2.0.so.0 libglib-2.0.so.0 libgobject-2.0.so.0 \
               libgio-2.0.so.0 libpango-1.0.so.0 libcairo.so.2 libgdk_pixbuf-2.0.so.0; do
    [ -e "$libdir/$library" ] && hide+=(--ro-bind /dev/null "$libdir/$library")
done
bwrap --dev-bind / / "${hide[@]}" --chdir "$work" env -u DISPLAY -u GI_TYPELIB_PATH -u XDG_DATA_DIRS \
    WAYLAND_DISPLAY="$socket" GDK_BACKEND=wayland NO_AT_BRIDGE=1 \
    "$work/venv/bin/python" -c 'from PyLiite4 import Gdk, Gtk; Gtk.init(); print(type(Gdk.Display.get_default()).__name__)'
bwrap --dev-bind / / "${hide[@]}" --chdir "$work" env -u DISPLAY -u GI_TYPELIB_PATH -u XDG_DATA_DIRS \
    WAYLAND_DISPLAY="$socket" GDK_BACKEND=wayland NO_AT_BRIDGE=1 \
    "$work/venv/bin/python" -m pytest -q --no-header -p no:cacheprovider --tb=short -W ignore tests
