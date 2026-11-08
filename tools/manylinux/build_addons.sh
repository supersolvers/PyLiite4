#!/bin/bash
# Build the libraries of the PyLiite4-Addons wheel into /opt/addons, on top of the stack in /opt/gtk:
# WebKitGTK, libshumate, libspelling, VTE, Gom, libmanette and glycin, with what they need that the main wheel doesn't
# have.
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
    woff2-devel lz4-devel json-glib-devel protobuf-c-devel libevdev-devel libgudev-devel libseccomp-devel nasm bubblewrap \
    unifdef ruby rubygems rubygem-json ruby-default-gems perl perl-FindBin perl-JSON-PP perl-English \
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
meson_package libspelling $GNOME/libspelling/0.4/libspelling-0.4.11.tar.xz -Denchant=enabled -Dintrospection=enabled \
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

# glycin (Gly), which decodes images in sandboxed helper programs: image-rs for PNG, JPEG, GIF, WebP, TIFF and more,
# libheif for HEIF and AVIF, libjxl for JPEG XL, and librsvg for SVG. libheif decodes only, with dav1d and libde265.
# glycin's bindings are for libjxl 0.11.
cmake_package highway https://github.com/google/highway/releases/download/1.4.0/highway-1.4.0.tar.gz \
    -DBUILD_SHARED_LIBS=ON -DBUILD_TESTING=OFF -DHWY_ENABLE_TESTS=OFF -DHWY_ENABLE_EXAMPLES=OFF -DHWY_ENABLE_CONTRIB=OFF
cmake_package libjxl https://github.com/libjxl/libjxl/archive/refs/tags/v0.11.2.tar.gz -DBUILD_TESTING=OFF \
    -DJPEGXL_FORCE_SYSTEM_HWY=ON -DJPEGXL_FORCE_SYSTEM_BROTLI=ON -DJPEGXL_FORCE_SYSTEM_LCMS2=ON -DJPEGXL_ENABLE_SKCMS=OFF \
    -DJPEGXL_ENABLE_TOOLS=OFF -DJPEGXL_ENABLE_JPEGLI=OFF -DJPEGXL_ENABLE_BENCHMARK=OFF -DJPEGXL_ENABLE_EXAMPLES=OFF \
    -DJPEGXL_ENABLE_MANPAGES=OFF -DJPEGXL_ENABLE_DOXYGEN=OFF -DJPEGXL_ENABLE_SJPEG=OFF -DJPEGXL_ENABLE_OPENEXR=OFF \
    -DJPEGXL_ENABLE_PLUGINS=OFF -DJPEGXL_ENABLE_FUZZERS=OFF -DJPEGXL_ENABLE_DEVTOOLS=OFF -DJPEGXL_ENABLE_JNI=OFF \
    -DJPEGXL_ENABLE_VIEWERS=OFF -DJPEGXL_BUNDLE_LIBPNG=OFF
cmake_package libde265 https://github.com/strukturag/libde265/releases/download/v1.1.3/libde265-1.1.3.tar.gz \
    -DENABLE_SDL=OFF -DENABLE_DECODER=OFF -DENABLE_ENCODER=OFF
meson_package dav1d https://downloads.videolan.org/pub/videolan/dav1d/1.5.4/dav1d-1.5.4.tar.xz -Denable_tools=false \
    -Denable_tests=false -Denable_examples=false
cmake_package libheif https://github.com/strukturag/libheif/releases/download/v1.23.7/libheif-1.23.7.tar.gz \
    -DBUILD_TESTING=OFF -DWITH_EXAMPLES=OFF -DWITH_GDK_PIXBUF=OFF -DENABLE_PLUGIN_LOADING=OFF -DWITH_LIBDE265=ON \
    -DWITH_DAV1D=ON -DWITH_AOM_DECODER=OFF -DWITH_AOM_ENCODER=OFF -DWITH_X265=OFF -DWITH_SvtEnc=OFF -DWITH_RAV1E=OFF \
    -DWITH_KVAZAAR=OFF -DWITH_FFMPEG_DECODER=OFF -DWITH_JPEG_DECODER=OFF -DWITH_JPEG_ENCODER=OFF \
    -DWITH_OpenJPEG_DECODER=OFF -DWITH_OpenJPEG_ENCODER=OFF -DWITH_OPENJPH_ENCODER=OFF -DWITH_LIBSHARPYUV=OFF
# glycin's sandbox needs access to the installed wheels as well as /usr and the loader binary. Patch glycin-core
# to mount PYLIITE4_SANDBOX_PATHS read-only. glycin normally fetches that crate from crates.io, so point Cargo at
# the patched local copy.
if [ ! -f /src/stamps/glycin ]; then
    glycin=$(fetch $GNOME/glycin/2.2/glycin-2.2.6.tar.xz)
    core=$(fetch https://static.crates.io/crates/glycin-core/glycin-core-4.0.5.crate)
    patch_once "$core" glycin-core-sandbox-paths.patch
    grep -q '^\[patch.crates-io\]' "$glycin/Cargo.toml" \
        || printf '\n[patch.crates-io]\nglycin-core = { path = "%s" }\n' "$core" >> "$glycin/Cargo.toml"
fi
# glycin 2.2 needs Rust 1.93, newer than AlmaLinux's, so it builds with the official toolchain, checked against its
# published checksum. The toolchain is only for building, and nothing of it goes in the wheel.
RUST=1.93.0
if [ ! -x /opt/rust-$RUST/bin/cargo ] && [ ! -f /src/stamps/glycin ]; then
    toolchain=rust-$RUST-$(uname -m)-unknown-linux-gnu
    url=https://static.rust-lang.org/dist/$toolchain.tar.xz
    curl -fsSL --retry 5 -o "/src/archives/$toolchain.tar.xz" "$url"
    (cd /src/archives && echo "$(curl -fsSL "$url.sha256" | cut -d' ' -f1)  $toolchain.tar.xz" | sha256sum -c --quiet -)
    tar xf "/src/archives/$toolchain.tar.xz" -C /tmp
    "/tmp/$toolchain/install.sh" --prefix=/opt/rust-$RUST --components=rustc,cargo,rust-std-$(uname -m)-unknown-linux-gnu \
        > /dev/null
    rm -rf "/tmp/$toolchain" "/src/archives/$toolchain.tar.xz"
fi
# Cargo doesn't read LDFLAGS, and without them the linker can find AlmaLinux's older GLib for the stack's libraries.
PATH=/opt/rust-$RUST/bin:$PATH RUSTFLAGS="-C link-arg=-L/opt/gtk/lib -C link-arg=-Wl,-rpath-link,$PREFIX/lib:/opt/gtk/lib" \
    meson_package glycin $GNOME/glycin/2.2/glycin-2.2.6.tar.xz -Dlibglycin=true -Dlibglycin-gtk4=true \
    -Dintrospection=true -Dvapi=false -Dcapi_docs=false -Dglycin-loaders=true \
    -Dloaders=glycin-heif,glycin-image-rs,glycin-jxl,glycin-svg \
    -Dglycin-thumbnailer=false -Dtests=false

# WebKit's sandbox runs xdg-dbus-proxy, which the wheel carries next to WebKit's processes.
meson_package xdg-dbus-proxy https://github.com/flatpak/xdg-dbus-proxy/releases/download/0.1.9/xdg-dbus-proxy-0.1.9.tar.xz \
    -Dman=disabled -Dtests=false

[ -f /src/stamps/webkitgtk ] || patch_once "$(fetch https://webkitgtk.org/releases/webkitgtk-2.54.2.tar.xz)" \
    webkitgtk-exec-path.patch
[ -f /src/stamps/webkitgtk ] || patch_once /src/webkitgtk-2.54.2 webkitgtk-sandbox-paths.patch
# Put the helper processes next to the library and point WEBKIT_EXEC_PATH there. The sandbox patches find bwrap
# on PATH, xdg-dbus-proxy beside the helpers, and mount the wheel's folders. The paths below are fallbacks.
# Name FreeType and Fontconfig explicitly so CMake doesn't pick AlmaLinux's older copies.
# Each WebKit compile job can take several GB. Use half the cores; a job per core exhausted memory on a 24-core,
# 128 GB machine.
JOBS=$(( (JOBS + 1) / 2 )) cmake_package webkitgtk https://webkitgtk.org/releases/webkitgtk-2.54.2.tar.xz -DPORT=GTK \
    -DUSE_GTK4=ON -DICU_ROOT="$PREFIX" \
    -DCMAKE_PREFIX_PATH="$PREFIX;/opt/gtk" -DFREETYPE_LIBRARY_RELEASE=/opt/gtk/lib/libfreetype.so \
    -DFontconfig_LIBRARY=/opt/gtk/lib/libfontconfig.so -DHarfBuzz_LIBRARY=/opt/gtk/lib/libharfbuzz.so \
    -DLIBEXEC_INSTALL_DIR="$PREFIX/lib/webkitgtk-6.0" -DENABLE_BUBBLEWRAP_SANDBOX=ON -DBWRAP_EXECUTABLE=/usr/bin/bwrap \
    -DDBUS_PROXY_EXECUTABLE=/usr/bin/xdg-dbus-proxy -DENABLE_DOCUMENTATION=OFF \
    -DENABLE_INTROSPECTION=ON -DENABLE_JOURNALD_LOG=OFF -DENABLE_MINIBROWSER=OFF -DENABLE_WEBDRIVER=OFF \
    -DENABLE_GAMEPAD=OFF -DENABLE_SPEECH_SYNTHESIS=OFF -DUSE_FLITE=OFF -DUSE_LIBBACKTRACE=OFF -DUSE_LIBHYPHEN=OFF \
    -DUSE_LIBSECRET=OFF -DUSE_SYSTEM_SYSPROF_CAPTURE=OFF -DUSE_JPEGXL=OFF -DUSE_AVIF=OFF -DUSE_GSTREAMER_WEBRTC=OFF \
    -DENABLE_WEB_RTC=OFF -DENABLE_MEDIA_STREAM=OFF -DUSE_SPIEL=OFF
echo "=== add-ons complete ($(date +%T))"
