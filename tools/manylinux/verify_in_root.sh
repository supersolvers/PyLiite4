#!/bin/bash
# Test a wheel inside the manylinux root, on its old glibc, with the built stack hidden.
# Needs a host Xvfb, which this script starts on a private display.
#
# Usage: tools/manylinux/verify_in_root.sh ROOT WHEEL [PYTHON_TAG] [ADDON_WHEEL...]
set -euo pipefail
root=$(realpath "$1"); wheel=$(realpath "$2"); tag=${3:-cp314}
# The add-on wheels, PyLiite4-Addons and PyLiite4-Poppler, if given, and their builds hidden like the stack's.
extra=()
for addons in "${@:4}"; do addons=$(realpath "$addons"); extra+=(--ro-bind "$addons" /tmp/wheel/"${addons##*/}"); done
for prefix in addons poppler; do
    if [ -d "$root/opt/$prefix" ]; then extra+=(--tmpfs "/opt/$prefix"); fi
done
project=$(cd "$(dirname "$0")/../.." && pwd)
# The test plugin needs D-Bus, Xvfb and libXtst. AppArmor restrictions on unprivileged bwrap can prevent nested
# sandboxes here, so WebKit's sandbox is off and glycin falls back. tools/verify_wheel.sh tests both sandboxes
# outside the outer bwrap. Unpack dbus-daemon's files directly: installing its package needs a system bus group
# that this user namespace doesn't have.
"$project/tools/manylinux/enter.sh" "$root" bash -c '
    dnf -y -q --setopt=install_weak_deps=False install xorg-x11-server-Xvfb libXtst cpio bubblewrap > /dev/null 2>&1 || true
    if [ ! -x /usr/bin/dbus-daemon ]; then
        cd /tmp && dnf -q download dbus-daemon && rpm2cpio dbus-daemon-*.rpm | (cd / && cpio -idm --quiet --no-preserve-owner)
    fi'
display=$((90 + RANDOM % 400))
Xvfb ":$display" -screen 0 1024x768x24 >/dev/null 2>&1 &
xvfb=$!
trap 'kill $xvfb' EXIT
sleep 1
bwrap --bind "$root" / --dev /dev --proc /proc --tmpfs /tmp --tmpfs /opt/gtk --ro-bind /etc/resolv.conf /etc/resolv.conf \
    --ro-bind "$wheel" /tmp/wheel/"${wheel##*/}" "${extra[@]}" --ro-bind "$project/tests" /tmp/run/tests \
    --ro-bind "$project/examples" /tmp/run/examples --ro-bind "$project/demos" /tmp/run/demos \
    --tmpfs /tmp/.X11-unix --ro-bind "/tmp/.X11-unix/X$display" "/tmp/.X11-unix/X$display" \
    --unshare-user --uid 0 --gid 0 --clearenv --setenv HOME /tmp/home --setenv LANG C.UTF-8 \
    --setenv WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS 1 \
    --setenv PATH /usr/bin:/bin --setenv DISPLAY ":$display" --setenv GDK_BACKEND x11 --setenv NO_AT_BRIDGE 1 \
    --chdir /tmp/run bash -c "ldd --version | head -1
        /opt/python/$tag-$tag/bin/python -m venv /tmp/venv
        /tmp/venv/bin/pip -q install /tmp/wheel/*.whl pytest mypy
        /tmp/venv/bin/python -m pytest -q --no-header -p no:cacheprovider --tb=short -W ignore tests"
