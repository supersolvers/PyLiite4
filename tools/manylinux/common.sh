# Helpers shared by build_stack.sh and build_addons.sh. Set PREFIX before calling them.
GNOME=https://download.gnome.org/sources
GST=https://gstreamer.freedesktop.org/src
JOBS=$(nproc)
mkdir -p /src/stamps /src/archives
cd /src

fetch() { # url -> prints the unpacked directory
    local archive="/src/archives/${1##*/}"
    [ -f "$archive" ] || curl -fsSL --retry 5 --retry-all-errors --connect-timeout 30 --max-time 300 -o "$archive" "$1"
    local directory
    # tar may die of SIGPIPE once head has its line, which pipefail would treat as a failure.
    directory=$(tar tf "$archive" | head -1 | cut -d/ -f1 || true)
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

cmake_package() { # stamp url cmake-options...
    local stamp=$1 url=$2; shift 2
    [ -f "/src/stamps/$stamp" ] && return
    echo "=== $stamp ($(date +%T))"
    local source build=/src/build-$stamp
    source=$(fetch "$url")
    cmake -S "$source" -B "$build" -G Ninja -DCMAKE_INSTALL_PREFIX="$PREFIX" -DCMAKE_INSTALL_LIBDIR=lib \
        -DCMAKE_BUILD_TYPE=Release "$@" > "/src/$stamp.setup.log" 2>&1 || { tail -30 "/src/$stamp.setup.log"; exit 1; }
    ninja -C "$build" -j "$JOBS" install > "/src/$stamp.log" 2>&1 || { tail -30 "/src/$stamp.log"; exit 1; }
    touch "/src/stamps/$stamp"
}
