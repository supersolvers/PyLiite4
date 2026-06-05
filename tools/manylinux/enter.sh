#!/bin/bash
# Run a command inside an unpacked manylinux root, with the project at /project.
#
# Usage: tools/manylinux/enter.sh ROOT COMMAND...
set -euo pipefail
root=$(realpath "$1"); shift
project=$(cd "$(dirname "$0")/../.." && pwd)
exec bwrap --bind "$root" / --dev /dev --proc /proc --tmpfs /tmp --ro-bind /etc/resolv.conf /etc/resolv.conf \
    --bind "$project" /project --unshare-user --uid 0 --gid 0 --clearenv \
    --setenv HOME /root --setenv LANG C.UTF-8 \
    --setenv PATH /opt/gtk/bin:/opt/tools/bin:/opt/rh/gcc-toolset-14/root/usr/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin \
    --setenv PKG_CONFIG_PATH /opt/gtk/lib/pkgconfig:/opt/gtk/share/pkgconfig \
    --setenv LD_LIBRARY_PATH /opt/gtk/lib:/opt/rh/gcc-toolset-14/root/usr/lib64 \
    --setenv XDG_DATA_DIRS /opt/gtk/share:/usr/share \
    --setenv GI_TYPELIB_PATH /opt/gtk/lib/girepository-1.0 \
    "$@"
