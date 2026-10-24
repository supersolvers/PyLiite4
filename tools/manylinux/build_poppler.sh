#!/bin/bash
# Build Poppler's GLib library into /opt/poppler, on top of the stack in /opt/gtk, for the PyLiite4-Poppler wheel.
# Poppler is GPL, so it ships apart from the LGPL wheels. Run build_stack.sh first. Finished packages are recorded in
# /src/stamps, as there.
#
# Usage: tools/manylinux/enter.sh ROOT /project/tools/manylinux/build_poppler.sh
set -euo pipefail

PREFIX=/opt/poppler
mkdir -p "$PREFIX"
source "$(dirname "$0")/common.sh"
export PKG_CONFIG_PATH=$PREFIX/lib/pkgconfig:$PKG_CONFIG_PATH
export LD_LIBRARY_PATH=$PREFIX/lib:$LD_LIBRARY_PATH
export GI_TYPELIB_PATH=$PREFIX/lib/girepository-1.0:$GI_TYPELIB_PATH
export LIBRARY_PATH=/opt/gtk/lib
export LDFLAGS="-L/opt/gtk/lib -Wl,-rpath-link,/opt/gtk/lib"

dnf -y -q --setopt=install_weak_deps=False install openjpeg2-devel lcms2-devel libjpeg-turbo-devel || true

# Only the GLib frontend, drawing with Cairo. Signatures (NSS, GPGME), network access, Boost and Brotli (AlmaLinux's is too old) are left out, and so
# is poppler-data: Poppler would look for it at its build prefix.
cmake_package poppler https://poppler.freedesktop.org/poppler-26.10.0.tar.xz -DCMAKE_PREFIX_PATH=/opt/gtk \
    -DFREETYPE_LIBRARY_RELEASE=/opt/gtk/lib/libfreetype.so -DFontconfig_LIBRARY=/opt/gtk/lib/libfontconfig.so \
    -DENABLE_GLIB=ON -DENABLE_GOBJECT_INTROSPECTION=ON -DENABLE_CPP=OFF -DENABLE_QT5=OFF -DENABLE_QT6=OFF \
    -DENABLE_UTILS=OFF -DENABLE_NSS3=OFF -DENABLE_GPGME=OFF -DENABLE_LIBCURL=OFF -DENABLE_BOOST=OFF -DENABLE_BROTLI=OFF \
    -DENABLE_LCMS=ON -DENABLE_LIBOPENJPEG=openjpeg2 -DENABLE_DCTDECODER=libjpeg -DENABLE_LIBTIFF=ON \
    -DBUILD_GTK_TESTS=OFF -DBUILD_CPP_TESTS=OFF -DBUILD_MANUAL_TESTS=OFF -DBUILD_QT5_TESTS=OFF \
    -DBUILD_QT6_TESTS=OFF -DENABLE_GTK_DOC=OFF -DTESTDATADIR=/nonexistent
echo "=== poppler complete ($(date +%T))"
