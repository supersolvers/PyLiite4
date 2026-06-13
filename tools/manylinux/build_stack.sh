#!/bin/bash
# Build GTK 4, libadwaita and their dependencies into /opt/gtk, inside a manylinux root.
# Finished packages are recorded in /src/stamps, so a failed build resumes where it stopped.
#
# Usage: tools/manylinux/enter.sh ROOT /project/tools/manylinux/build_stack.sh
set -euo pipefail

PREFIX=/opt/gtk
GNOME=https://download.gnome.org/sources
GST=https://gstreamer.freedesktop.org/src
JOBS=$(nproc)
mkdir -p /src/stamps /src/archives "$PREFIX"
cd /src

dnf -y -q --setopt=install_weak_deps=False install bison flex gperf gettext-devel pcre2-devel libffi-devel zlib-devel \
    expat-devel libpng-devel libjpeg-turbo-devel libtiff-devel freetype-devel fontconfig-devel libxml2-devel dbus-devel \
    libX11-devel libXext-devel libXrender-devel libXi-devel libXrandr-devel libXcursor-devel libXdamage-devel \
    libXfixes-devel libXinerama-devel libxkbcommon-devel libxcb-devel mesa-libEGL-devel mesa-libGL-devel \
    mesa-libgbm-devel libdrm-devel vulkan-headers vulkan-loader-devel libmount-devel cups-devel pixman-devel \
    libogg-devel libvorbis-devel opus-devel libvpx-devel pulseaudio-libs-devel orc-devel lcms2-devel shared-mime-info glslc libyaml-devel libcurl-devel libxmlb-devel libxslt itstool docbook-style-xsl docbook-dtds cargo rust cargo-c iso-codes-devel python3 \
    || true
dnf -y -q --setopt=install_weak_deps=False --enablerepo=crb install libtheora-devel || true
# g-ir-scanner puts /usr/lib64 first on the library path, where the toolset's linker would find an old libctf.
for library in libctf.so.0 libctf-nobfd.so.0; do
    ln -sf "/opt/rh/gcc-toolset-14/root/usr/lib64/$library" "/usr/lib64/$library"
done
[ -x /opt/tools/bin/meson ] || { /opt/python/cp314-cp314/bin/python -m venv /opt/tools
    /opt/tools/bin/pip -q install meson==1.12.1 ninja packaging setuptools; }

fetch() { # url -> prints the unpacked directory
    local archive="/src/archives/${1##*/}"
    [ -f "$archive" ] || curl -fsSL --retry 5 --retry-all-errors --connect-timeout 30 --max-time 300 -o "$archive" "$1"
    local directory
    directory=$(tar tf "$archive" | head -1 | cut -d/ -f1)
    [ -d "/src/$directory" ] || tar xf "$archive" -C /src --no-same-owner
    echo "/src/$directory"
}

meson_package() { # stamp url meson-options...
    local stamp=$1 url=$2; shift 2
    [ -f "/src/stamps/$stamp" ] && return
    echo "=== $stamp ($(date +%T))"
    local source build
    source=$(fetch "$url")
    build="/src/build-$stamp"
    local mode=()
    [ -d "$build/meson-private" ] && mode=(--wipe)
    meson setup "${mode[@]}" "$build" "$source" --prefix="$PREFIX" --libdir=lib --buildtype=release \
        --wrap-mode=nodownload -Dauto_features=auto "$@" > "/src/$stamp.setup.log" 2>&1 \
        || { tail -30 "/src/$stamp.setup.log"; exit 1; }
    ninja -C "$build" -j "$JOBS" install > "/src/$stamp.log" 2>&1 || { tail -30 "/src/$stamp.log"; exit 1; }
    touch "/src/stamps/$stamp"
}

meson_package wayland https://gitlab.freedesktop.org/wayland/wayland/-/releases/1.24.0/downloads/wayland-1.24.0.tar.xz \
    -Ddocumentation=false -Dtests=false
meson_package wayland-protocols \
    https://gitlab.freedesktop.org/wayland/wayland-protocols/-/releases/1.45/downloads/wayland-protocols-1.45.tar.xz \
    -Dtests=false
meson_package glib-bootstrap $GNOME/glib/2.86/glib-2.86.5.tar.xz \
    -Dintrospection=disabled -Dtests=false -Dman-pages=disabled -Ddocumentation=false -Dsysprof=disabled -Dselinux=disabled
meson_package gobject-introspection $GNOME/gobject-introspection/1.86/gobject-introspection-1.86.0.tar.xz \
    -Dbuild_introspection_data=true
meson_package glib $GNOME/glib/2.86/glib-2.86.5.tar.xz \
    -Dintrospection=enabled -Dtests=false -Dman-pages=disabled -Ddocumentation=false -Dsysprof=disabled -Dselinux=disabled
meson_package fribidi https://github.com/fribidi/fribidi/releases/download/v1.0.16/fribidi-1.0.16.tar.xz \
    -Ddocs=false -Dtests=false
meson_package cairo https://www.cairographics.org/releases/cairo-1.18.4.tar.xz -Dtests=disabled -Dgtk_doc=false
meson_package harfbuzz https://github.com/harfbuzz/harfbuzz/releases/download/12.3.2/harfbuzz-12.3.2.tar.xz \
    -Dtests=disabled -Ddocs=disabled -Dgobject=enabled -Dintrospection=enabled -Dcairo=enabled -Dfreetype=enabled
meson_package pango $GNOME/pango/1.57/pango-1.57.1.tar.xz -Dintrospection=enabled -Dbuild-testsuite=false \
    -Dbuild-examples=false -Ddocumentation=false -Dman-pages=false
# AlmaLinux's libtiff links the GPL-only libjbig, so build one without JBIG support.
if [ ! -f /src/stamps/tiff ]; then
    echo "=== tiff ($(date +%T))"
    tiff=$(fetch https://download.osgeo.org/libtiff/tiff-4.7.1.tar.xz)
    cmake -S "$tiff" -B /src/build-tiff -G Ninja -DCMAKE_INSTALL_PREFIX="$PREFIX" -DCMAKE_INSTALL_LIBDIR=lib \
        -DCMAKE_BUILD_TYPE=Release -Djbig=OFF -Dlerc=OFF -Dlibdeflate=OFF -Dcxx=OFF -Dtiff-tools=OFF \
        -Dtiff-tests=OFF -Dtiff-contrib=OFF -Dtiff-docs=OFF > /src/tiff.setup.log 2>&1 \
        || { tail -30 /src/tiff.setup.log; exit 1; }
    ninja -C /src/build-tiff -j "$JOBS" install > /src/tiff.log 2>&1 || { tail -30 /src/tiff.log; exit 1; }
    touch /src/stamps/tiff
fi
meson_package gdk-pixbuf $GNOME/gdk-pixbuf/2.44/gdk-pixbuf-2.44.8.tar.xz -Dintrospection=enabled -Dtests=false \
    -Dinstalled_tests=false -Dman=false -Ddocumentation=false -Dglycin=disabled -Dgif=enabled -Dpng=enabled \
    -Djpeg=enabled -Dtiff=enabled -Dothers=enabled
meson_package graphene $GNOME/graphene/1.10/graphene-1.10.8.tar.xz -Dtests=false -Dintrospection=enabled \
    -Dinstalled_tests=false
meson_package libepoxy https://github.com/anholt/libepoxy/archive/refs/tags/1.5.10.tar.gz -Dtests=false -Ddocs=false
meson_package gstreamer $GST/gstreamer/gstreamer-1.26.5.tar.xz -Dintrospection=disabled -Dtests=disabled \
    -Dexamples=disabled -Ddoc=disabled -Dtools=enabled -Dbash-completion=disabled -Dlibdw=disabled -Dlibunwind=disabled
meson_package gst-plugins-base $GST/gst-plugins-base/gst-plugins-base-1.26.5.tar.xz -Dintrospection=disabled \
    -Dtests=disabled -Dexamples=disabled -Ddoc=disabled -Dtools=disabled -Dcdparanoia=disabled -Dalsa=disabled \
    -Dpango=disabled -Dgl_api=opengl,gles2 -Dgl_platform=egl,glx -Dgl_winsys=egl,x11,wayland
meson_package gst-plugins-good $GST/gst-plugins-good/gst-plugins-good-1.26.5.tar.xz -Dtests=disabled \
    -Dexamples=disabled -Ddoc=disabled -Dauto_features=disabled -Disomp4=enabled -Dmatroska=enabled -Dwavparse=enabled \
    -Dautodetect=enabled -Dpulse=enabled -Dvpx=enabled -Daudiofx=enabled
meson_package gst-plugins-bad $GST/gst-plugins-bad/gst-plugins-bad-1.26.5.tar.xz -Dtests=disabled -Dexamples=disabled \
    -Ddoc=disabled -Dintrospection=disabled -Dauto_features=disabled -Dgpl=disabled

if [ ! -f /src/stamps/sassc ]; then
    echo "=== sassc ($(date +%T))"
    libsass=$(fetch https://github.com/sass/libsass/archive/refs/tags/3.6.6.tar.gz)
    sassc=$(fetch https://github.com/sass/sassc/archive/refs/tags/3.6.2.tar.gz)
    make -C "$sassc" -j "$JOBS" SASS_LIBSASS_PATH="$libsass" BUILD=static > /src/sassc.log 2>&1 \
        || { tail -30 /src/sassc.log; exit 1; }
    cp "$sassc/bin/sassc" "$PREFIX/bin/"
    touch /src/stamps/sassc
fi

meson_package gtk $GNOME/gtk/4.22/gtk-4.22.4.tar.xz -Dintrospection=enabled -Dbuild-demos=false -Dbuild-testsuite=false \
    -Dbuild-examples=false -Dbuild-tests=false -Ddocumentation=false -Dman-pages=false -Dscreenshots=false \
    -Dx11-backend=true -Dwayland-backend=true -Dbroadway-backend=false -Dmedia-gstreamer=enabled -Dprint-cups=enabled \
    -Dprint-cpdb=disabled -Dvulkan=enabled -Dcloudproviders=disabled -Dsysprof=disabled -Dtracker=disabled \
    -Dcolord=disabled -Daccesskit=disabled
meson_package appstream https://github.com/ximion/appstream/archive/refs/tags/v1.0.6.tar.gz -Dstemming=false \
    -Dsystemd=false -Dgir=false -Ddocs=false -Dapidocs=false -Dinstall-docs=false -Dvapi=false -Dqt=false -Dcompose=false
meson_package libadwaita $GNOME/libadwaita/1.9/libadwaita-1.9.4.tar.xz -Dintrospection=enabled -Dvapi=false \
    -Dtests=false -Dexamples=false -Ddocumentation=false
meson_package librsvg $GNOME/librsvg/2.60/librsvg-2.60.3.tar.xz -Dintrospection=disabled -Dpixbuf=enabled \
    -Dpixbuf-loader=enabled -Ddocs=disabled -Dvala=disabled -Dtests=false -Davif=disabled

if [ ! -f /src/stamps/ibus ]; then
    echo "=== ibus ($(date +%T))"
    ibus=$(fetch https://github.com/ibus/ibus/releases/download/1.5.34/ibus-1.5.34.tar.gz)
    # Only the client library and GTK 4 module: the daemon and its tools come from the user's system.
    (cd "$ibus" && ./configure --prefix="$PREFIX" --libdir="$PREFIX/lib" --enable-gtk4 --disable-gtk2 --disable-gtk3 \
        --disable-xim --disable-wayland --disable-dconf --disable-gconf --disable-memconf --disable-schemas-compile \
        --disable-setup --disable-ui --disable-engine --disable-emoji-dict --disable-unicode-dict --disable-appindicator \
        --disable-vala --disable-introspection --disable-gtk-doc --disable-libnotify --disable-tests \
        --disable-python2 --disable-python-library --disable-systemd-services
    ) > /src/ibus.setup.log 2>&1 || { tail -30 /src/ibus.setup.log; exit 1; }
    for part in src client/gtk4; do
        (make -C "$ibus/$part" -j "$JOBS" && make -C "$ibus/$part" install) >> /src/ibus.log 2>&1 \
            || { tail -30 /src/ibus.log; exit 1; }
    done
    touch /src/stamps/ibus
fi
echo "=== stack complete ($(date +%T))"
