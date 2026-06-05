#!/bin/bash
# Build bundled wheels from the stack in /opt/gtk, one per Python version.
#
# Usage: tools/manylinux/enter.sh ROOT /project/tools/manylinux/build_wheels.sh [cp310 cp311 ...]
set -euo pipefail
dnf -y -q --setopt=install_weak_deps=False install adwaita-icon-theme hicolor-icon-theme 2>&1 | tail -1 || true
versions=("${@:-cp310 cp311 cp312 cp313 cp314}")
for version in ${versions[*]}; do
    echo "=== $version"
    venv=/opt/venv-$version
    if [ ! -x "$venv/bin/python" ]; then
        "/opt/python/$version-$version/bin/python" -m venv "$venv"
        "$venv/bin/pip" -q install PyGObject==3.56.2 pycairo patchelf tomli
    fi
    PATH="$venv/bin:$PATH" "$venv/bin/python" /project/tools/build_wheel.py --prefix /opt/gtk --output /project/dist
done
