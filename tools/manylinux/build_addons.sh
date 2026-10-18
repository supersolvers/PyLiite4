#!/bin/bash
# Build the libraries of the PyLiite4-Addons wheel into /opt/addons, on top of the stack in /opt/gtk:
# WebKitGTK, libshumate, libspelling, VTE, Gom and libmanette, with what they need that the main wheel doesn't have.
# Run build_stack.sh first. Finished packages are recorded in /src/stamps, as there.
#
# Usage: tools/manylinux/enter.sh ROOT /project/tools/manylinux/build_addons.sh
set -euo pipefail

PREFIX=/opt/addons
mkdir -p "$PREFIX"
source "$(dirname "$0")/common.sh"
PATCHES=$(dirname "$0")/patches
export PKG_CONFIG_PATH=$PREFIX/lib/pkgconfig:$PREFIX/share/pkgconfig:$PKG_CONFIG_PATH
export LD_LIBRARY_PATH=$PREFIX/lib:$LD_LIBRARY_PATH
export XDG_DATA_DIRS=$PREFIX/share:$XDG_DATA_DIRS
export GI_TYPELIB_PATH=$PREFIX/lib/girepository-1.0:$GI_TYPELIB_PATH
export PATH=$PREFIX/bin:$PATH
# WebKit links some libraries, such as Wayland's, by name alone, and so does g-ir-scanner, which adds LDFLAGS.
# Otherwise the linker finds AlmaLinux's older GLib and HarfBuzz.
export LIBRARY_PATH=$PREFIX/lib:/opt/gtk/lib
export LDFLAGS="-L$PREFIX/lib -L/opt/gtk/lib -Wl,-rpath-link,$PREFIX/lib:/opt/gtk/lib"

dnf -y -q --setopt=install_weak_deps=False install libwebp-devel libxslt-devel libgcrypt-devel libtasn1-devel \
    woff2-devel lz4-devel json-glib-devel protobuf-c-devel libevdev-devel libgudev-devel unifdef ruby rubygems rubygem-json ruby-default-gems perl perl-FindBin perl-JSON-PP perl-English \
    || true

patch_once() { # source-directory patch
    [ -f "$1/.pyliite4-$2" ] && return
    patch -d "$1" -p1 < "$PATCHES/$2"
    touch "$1/.pyliite4-$2"
}

autotools_package() { # stamp url subdirectory configure-options...
    local stamp=$1 url=$2 subdirectory=$3; shift 3
    [ -f "/src/stamps/$stamp" ] && return
    echo "=== $stamp ($(date +%T))"
    local source
    source=$(fetch "$url")/$subdirectory
    (cd "$source" && ./configure --prefix="$PREFIX" --libdir="$PREFIX/lib" "$@") > "/src/$stamp.setup.log" 2>&1 \
        || { tail -30 "/src/$stamp.setup.log"; exit 1; }
    (make -C "$source" -j "$JOBS" && make -C "$source" install) > "/src/$stamp.log" 2>&1 \
        || { tail -30 "/src/$stamp.log"; exit 1; }
    touch "/src/stamps/$stamp"
}

# WebKitGTK needs ICU 70.1 or newer, and AlmaLinux 9 has 67. HarfBuzz's ICU library is rebuilt against it; the
# add-ons wheel takes only libharfbuzz-icu from that build and the rest from the main wheel, which is the same version.
autotools_package icu https://github.com/unicode-org/icu/releases/download/release-79.1/icu4c-79.1-sources.tgz source \
    --disable-samples --disable-tests --disable-extras --disable-icuio --disable-layoutex
meson_package harfbuzz-icu https://github.com/harfbuzz/harfbuzz/releases/download/12.3.2/harfbuzz-12.3.2.tar.xz \
    -Dtests=disabled -Ddocs=disabled -Dgobject=disabled -Dintrospection=disabled -Dcairo=disabled -Dfreetype=enabled \
    -Dicu=enabled -Dutilities=disabled
# Only libharfbuzz-icu is wanted from that build: the rest would shadow the same libraries in /opt/gtk.
rm -f "$PREFIX"/lib/libharfbuzz{,-subset,-cairo,-gobject}.so* "$PREFIX"/lib/pkgconfig/harfbuzz{,-subset,-cairo,-gobject}.pc

# Spell checking: Hunspell for the dictionaries the user's system has, through Enchant.
autotools_package hunspell https://github.com/hunspell/hunspell/releases/download/v1.7.6/hunspell-1.7.6.tar.gz . \
    --disable-static --without-ui --without-readline
autotools_package enchant https://github.com/rrthomas/enchant/releases/download/v2.8.21/enchant-2.8.21.tar.gz . \
    --disable-static --enable-relocatable --with-hunspell --without-aspell --without-hspell --without-nuspell \
    --without-voikko --without-zemberek --without-applespell
# A Checker made without a provider takes the default one without a reference, then releases one when freed.
patch_once "$(fetch $GNOME/libspelling/0.4/libspelling-0.4.10.tar.xz)" libspelling-checker-ref.patch
meson_package libspelling $GNOME/libspelling/0.4/libspelling-0.4.10.tar.xz -Denchant=enabled -Dintrospection=enabled \
    -Dvapi=false -Ddocs=false -Dsysprof=false

meson_package vte $GNOME/vte/0.84/vte-0.84.1.tar.xz -Dgtk3=false -Dgtk4=true -Dgir=true -Dvapi=false -Ddocs=false \
    -Dgnutls=false -D_systemd=false -Dicu=true -Dglade=false -Dapp=false
meson_package libshumate $GNOME/libshumate/1.7/libshumate-1.7.0.tar.xz -Dgir=true -Dvapi=false -Dgtk_doc=false \
    -Ddemos=false -Dvector_renderer=false -Dsysprof=disabled
meson_package gom $GNOME/gom/0.5/gom-0.5.6.tar.xz -Denable-introspection=true -Denable-gtk-doc=false
# libmanette reads gamepads through hidraw; AlmaLinux has hidapi only in EPEL.
cmake_package hidapi https://github.com/libusb/hidapi/archive/refs/tags/hidapi-0.15.0.tar.gz -DHIDAPI_WITH_LIBUSB=OFF \
    -DHIDAPI_BUILD_HIDTEST=OFF
meson_package libmanette $GNOME/libmanette/0.2/libmanette-0.2.13.tar.xz -Dintrospection=true -Dvapi=false \
    -Ddemos=false -Dbuild-tests=false -Dinstall-tests=false -Dgudev=enabled

[ -f /src/stamps/webkitgtk ] || patch_once "$(fetch https://webkitgtk.org/releases/webkitgtk-2.54.2.tar.xz)" \
    webkitgtk-exec-path.patch
# The helper processes go next to the library, where the bundle points WEBKIT_EXEC_PATH. No bubblewrap sandbox: it
# needs bwrap and xdg-dbus-proxy on the user's system, which a wheel can't count on.
# CMake's own FreeType and Fontconfig searches would find AlmaLinux's older ones, so they are named.
cmake_package webkitgtk https://webkitgtk.org/releases/webkitgtk-2.54.2.tar.xz -DPORT=GTK -DUSE_GTK4=ON -DICU_ROOT="$PREFIX" \
    -DCMAKE_PREFIX_PATH="$PREFIX;/opt/gtk" -DFREETYPE_LIBRARY_RELEASE=/opt/gtk/lib/libfreetype.so \
    -DFontconfig_LIBRARY=/opt/gtk/lib/libfontconfig.so -DHarfBuzz_LIBRARY=/opt/gtk/lib/libharfbuzz.so \
    -DLIBEXEC_INSTALL_DIR="$PREFIX/lib/webkitgtk-6.0" -DENABLE_BUBBLEWRAP_SANDBOX=OFF -DENABLE_DOCUMENTATION=OFF \
    -DENABLE_INTROSPECTION=ON -DENABLE_JOURNALD_LOG=OFF -DENABLE_MINIBROWSER=OFF -DENABLE_WEBDRIVER=OFF \
    -DENABLE_GAMEPAD=OFF -DENABLE_SPEECH_SYNTHESIS=OFF -DUSE_FLITE=OFF -DUSE_LIBBACKTRACE=OFF -DUSE_LIBHYPHEN=OFF \
    -DUSE_LIBSECRET=OFF -DUSE_SYSTEM_SYSPROF_CAPTURE=OFF -DUSE_JPEGXL=OFF -DUSE_AVIF=OFF -DUSE_GSTREAMER_WEBRTC=OFF \
    -DENABLE_WEB_RTC=OFF -DENABLE_MEDIA_STREAM=OFF -DUSE_SPIEL=OFF
echo "=== add-ons complete ($(date +%T))"
