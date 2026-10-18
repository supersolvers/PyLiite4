#!/bin/bash
# Test a wheel inside the manylinux root, on its old glibc, with the built stack hidden.
# Needs a host Xvfb, which this script starts on a private display.
#
# Usage: tools/manylinux/verify_in_root.sh ROOT WHEEL [PYTHON_TAG] [ADDONS_WHEEL]
set -euo pipefail
root=$(realpath "$1"); wheel=$(realpath "$2"); tag=${3:-cp314}
# The add-ons wheel, if given, and the add-ons' build hidden like the stack's.
extra=()
if [ -n "${4:-}" ]; then addons=$(realpath "$4"); extra+=(--ro-bind "$addons" /tmp/wheel/"${addons##*/}"); fi
if [ -d "$root/opt/addons" ]; then extra+=(--tmpfs /opt/addons); fi
project=$(cd "$(dirname "$0")/../.." && pwd)
display=$((90 + RANDOM % 400))
Xvfb ":$display" -screen 0 1024x768x24 >/dev/null 2>&1 &
xvfb=$!
trap 'kill $xvfb' EXIT
sleep 1
bwrap --bind "$root" / --dev /dev --proc /proc --tmpfs /tmp --tmpfs /opt/gtk --ro-bind /etc/resolv.conf /etc/resolv.conf \
    --ro-bind "$wheel" /tmp/wheel/"${wheel##*/}" "${extra[@]}" --ro-bind "$project/tests" /tmp/run/tests \
    --ro-bind "$project/examples" /tmp/run/examples --ro-bind "$project/demos" /tmp/run/demos \
    --ro-bind /tmp/.X11-unix /tmp/.X11-unix \
    --unshare-user --uid 0 --gid 0 --clearenv --setenv HOME /tmp/home --setenv LANG C.UTF-8 \
    --setenv PATH /usr/bin:/bin --setenv DISPLAY ":$display" --setenv GDK_BACKEND x11 --setenv NO_AT_BRIDGE 1 \
    --chdir /tmp/run bash -c "ldd --version | head -1
        /opt/python/$tag-$tag/bin/python -m venv /tmp/venv
        /tmp/venv/bin/pip -q install /tmp/wheel/*.whl pytest mypy
        /tmp/venv/bin/python -m pytest -q --no-header -p no:cacheprovider --tb=short -W ignore tests"
