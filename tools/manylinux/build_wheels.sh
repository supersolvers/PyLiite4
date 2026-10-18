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
    # GStreamer's PyGObject overrides include a C extension, so they're built for each Python version and installed
    # next to PyGObject's own, where build_wheel.py picks them up.
    if [ ! -f "/src/stamps/gst-python-$version" ]; then
        headers=$(echo "$venv"/include/site/python*/PyGObject)
        mkdir -p "$venv/lib/pkgconfig"
        printf 'Name: PyGObject\nDescription: PyGObject headers\nVersion: %s\nCflags: -I%s\n' \
            "$("$venv/bin/python" -c 'from importlib.metadata import version; print(version("PyGObject"))')" \
            "$headers/pygobject-3.0" > "$venv/lib/pkgconfig/pygobject-3.0.pc"
        overrides=$("$venv/bin/python" -c 'import gi.overrides, os; print(os.path.dirname(gi.overrides.__file__))')
        build=/src/build-gst-python-$version
        rm -rf "$build"
        PKG_CONFIG_PATH="$venv/lib/pkgconfig:$PKG_CONFIG_PATH" meson setup "$build" /src/gst-python-1.26.5 \
            --prefix="$venv" --libdir=lib --buildtype=release -Dpython-exe="$venv/bin/python" \
            -Dpygi-overrides-dir="$overrides" -Dplugin=disabled -Dtests=disabled > "/src/gst-python-$version.log" 2>&1 \
            && ninja -C "$build" install >> "/src/gst-python-$version.log" 2>&1 \
            || { tail -30 "/src/gst-python-$version.log"; exit 1; }
        touch "/src/stamps/gst-python-$version"
    fi
    PATH="$venv/bin:$PATH" "$venv/bin/python" /project/tools/build_wheel.py --prefix /opt/gtk --output /project/dist \
        --sources /project/dist/sources
    # The PyLiite4-Addons wheel, once build_addons.sh has built its libraries.
    if [ -f /src/stamps/webkitgtk ]; then
        PATH="$venv/bin:$PATH" "$venv/bin/python" /project/tools/build_addons_wheel.py --prefix /opt/gtk \
            --addons-prefix /opt/addons --output /project/dist --sources /project/dist/sources
    fi
done
