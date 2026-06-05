#!/usr/bin/env python3
"""Unpack a manylinux container image into a directory, without a container engine.

Usage: tools/manylinux/fetch_root.py TARGET [--image pypa/manylinux_2_34_x86_64]
"""

import argparse
import json
import subprocess
import tempfile
import urllib.request
from pathlib import Path

REGISTRY = "https://quay.io"
MANIFESTS = "application/vnd.oci.image.index.v1+json,application/vnd.docker.distribution.manifest.list.v2+json," \
            "application/vnd.oci.image.manifest.v1+json,application/vnd.docker.distribution.manifest.v2+json"


def fetch(url, token, accept=None):
    headers = {"Authorization": f"Bearer {token}"}
    if accept:
        headers["Accept"] = accept
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path)
    parser.add_argument("--image", default="pypa/manylinux_2_34_x86_64")
    parser.add_argument("--tag", default="latest")
    args = parser.parse_args()
    auth = f"{REGISTRY}/v2/auth?service=quay.io&scope=repository:{args.image}:pull"
    token = json.load(urllib.request.urlopen(auth))["token"]
    base = f"{REGISTRY}/v2/{args.image}"
    manifest = json.load(fetch(f"{base}/manifests/{args.tag}", token, MANIFESTS))
    if "manifests" in manifest:
        entry = next(m for m in manifest["manifests"] if m["platform"]["architecture"] == "amd64")
        manifest = json.load(fetch(f"{base}/manifests/{entry['digest']}", token, MANIFESTS))
    args.target.mkdir(parents=True, exist_ok=True)
    for index, layer in enumerate(manifest["layers"]):
        print(f"layer {index + 1}/{len(manifest['layers'])}: {layer['size'] / 1e6:.0f} MB", flush=True)
        with tempfile.NamedTemporaryFile() as archive, fetch(f"{base}/blobs/{layer['digest']}", token) as response:
            while chunk := response.read(1 << 20):
                archive.write(chunk)
            archive.flush()
            # Unprivileged, so ownership and device nodes can't be restored; the sandbox doesn't need them.
            result = subprocess.run(["tar", "-xf", archive.name, "-C", str(args.target), "--no-same-owner",
                                     "--exclude=dev/*", "--delay-directory-restore"], capture_output=True, text=True)
            if result.returncode:
                print(f"tar exit {result.returncode}:\n{result.stderr[-2000:]}", flush=True)
                errors = [l for l in result.stderr.splitlines() if "Cannot" in l]
                print(f"{len(errors)} files were not unpacked", flush=True)
            subprocess.run(["chmod", "-R", "u+rwX", str(args.target)])
    print(f"unpacked to {args.target}")


if __name__ == "__main__":
    main()
