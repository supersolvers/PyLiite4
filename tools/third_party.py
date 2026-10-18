"""Name the project, license and source of every file a wheel bundles.

build_wheel.py hands over each bundled file with the file it was copied from.
Every one must belong to a project whose license texts can be found, or the
build fails, so a wheel can't ship code without its notices. The source
archives of those projects can be collected for publishing next to a release.

Projects come from:
- the meson builds in /src, by their install logs (tools/manylinux/build_stack.sh)
- RPM packages of the manylinux root, by their source RPMs
- Debian packages, for wheels built on a Debian host (not for release)
- Python distributions on PyPI, and the Rust crates that librsvg compiles in
"""

import hashlib
import io
import json
import re
import shutil
import subprocess
import tarfile
import urllib.request
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path

try:
    import tomllib
except ImportError:  # Python 3.10
    import tomli as tomllib

SOURCE_TREE = Path("/src")
TEXTS = Path(__file__).resolve().parent / "license-texts"
LICENSE_NAME = re.compile(r"^(COPYING|LICEN[CS]E|COPYRIGHT|NOTICE|UNLICENSE)([._-].*)?$", re.I)
ARCHIVE = re.compile(r"\.(tar(\.(gz|xz|bz2|zst))?|tgz|tbz2)$")
# Meson projects that don't declare a license, or declare an old name for it.
MESON_LICENSES = {
    "cairo": "LGPL-2.1-only OR MPL-1.1",
    "freetype": "FTL OR GPL-2.0-or-later",
    "fribidi": "LGPL-2.1-or-later",
    "glib": "LGPL-2.1-or-later",
    "glib-networking": "LGPL-2.1-or-later",
    "gom": "LGPL-2.1-or-later",
    "gobject-introspection": "LGPL-2.0-or-later AND GPL-2.0-or-later AND MIT",
    "gst-python": "LGPL-2.1-or-later",
    "gstreamer": "LGPL-2.1-or-later",
    "gst-plugins-base": "LGPL-2.1-or-later",
    "gst-plugins-good": "LGPL-2.1-or-later",
    "gst-plugins-bad": "LGPL-2.1-or-later",
    "harfbuzz": "MIT-Modern-Variant",
    "libmanette": "LGPL-2.1-or-later",
    "libportal": "LGPL-3.0-only",
    "libshumate": "LGPL-2.1-or-later",
    "libspelling": "LGPL-2.1-or-later",
    "librsvg": "LGPL-2.1-or-later",
    "pango": "LGPL-2.1-or-later",
    "vte": "LGPL-3.0-or-later AND MIT AND (Apache-2.0 OR BSL-1.0 OR MIT) AND (Apache-2.0 OR MIT)",
    "wayland-protocols": "MIT",
}
# Projects that keep their license texts somewhere other than the top of their source tree.
OTHER_TEXTS = {"freetype": {"LICENSE.TXT", "docs/LICENSE.TXT", "docs/FTL.TXT", "docs/GPLv2.TXT"},
               "zlib": {"README"},
               # The libraries VTE compiles in.
               "vte": {"COPYING.XTERM", "subprojects/fast_float/LICENSE-APACHE", "subprojects/fast_float/LICENSE-BOOST",
                       "subprojects/fast_float/LICENSE-MIT", "subprojects/fmt/LICENSE",
                       "subprojects/simdutf/LICENSE-APACHE", "subprojects/simdutf/LICENSE-MIT"},
               # WebKit has no license file at the top, and compiles in these.
               "webkitgtk": {f"Source/{path}" for path in (
                   "WebCore/LICENSE-APPLE", "WebCore/LICENSE-LGPL-2", "WebCore/LICENSE-LGPL-2.1",
                   "JavaScriptCore/COPYING.LIB", "WTF/LICENSE-libc++.txt", "WTF/LICENSE-LLVM.txt", "WTF/LICENSE-simde.txt",
                   "WTF/LICENSE-dragonbox.txt", "WTF/icu/LICENSE", "WTF/wtf/dtoa/COPYING", "WTF/wtf/dtoa/LICENSE",
                   "WTF/wtf/fast_float/LICENSE", "WTF/wtf/simdutf/LICENSE-simdutf.txt", "bmalloc/mimalloc/mimalloc/LICENSE",
                   "ThirdParty/ANGLE/LICENSE", "ThirdParty/skia/LICENSE", "ThirdParty/libsysprof-capture/COPYING",
                   "ThirdParty/pdfjs/LICENSE", "JavaScriptCore/disassembler/zydis/LICENSE-zydis.txt",
                   "JavaScriptCore/disassembler/zydis/LICENSE-zycore.txt",
                   "JavaScriptCore/disassembler/ARM64/LICENSE-binja.txt")}}
# Projects with no license file at all, and the text in tools/license-texts that stands in for one.
STAND_IN_TEXTS = {"sqlite": "SQLite-blessing.txt"}
# Built with make or CMake rather than meson, so without an install log: their license and files, relative to a
# prefix. The add-ons' are in /opt/addons (tools/manylinux/build_addons.sh).
OTHER_BUILDS = {"ibus": ("LGPL-2.1-or-later", ["lib/libibus-1.0.so*", "lib/gtk-4.0/4.0.0/immodules/libim-ibus.so"]),
                "tiff": ("libtiff", ["lib/libtiff.so*"]),
                "icu": ("Unicode-3.0", ["lib/libicu*.so*"]),
                "hunspell": ("MPL-1.1 OR GPL-2.0-or-later OR LGPL-2.1-or-later", ["lib/libhunspell-*.so*"]),
                "enchant": ("LGPL-2.1-or-later", ["lib/libenchant-2.so*", "lib/enchant-2/*.so", "share/enchant-2/*"]),
                "hidapi": ("BSD-3-Clause OR GPL-3.0-only OR HIDAPI", ["lib/libhidapi-hidraw.so*"]),
                # Its own code, and the third-party code in OTHER_TEXTS.
                "webkitgtk": ("LGPL-2.1-or-later AND LGPL-2.0-or-later AND BSD-2-Clause AND BSD-3-Clause AND MIT AND "
                              "Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSL-1.0 AND Unicode-3.0 AND "
                              "BSD-2-Clause-Patent",
                              ["lib/libwebkitgtk-6.0.so*", "lib/libjavascriptcoregtk-6.0.so*", "lib/webkitgtk-6.0/**/*",
                               "lib/girepository-1.0/WebKit*.typelib", "lib/girepository-1.0/JavaScriptCore-6.0.typelib",
                               "share/locale/*/LC_MESSAGES/WebKitGTK-6.0.mo"])}
# Projects whose license mentions the GPL, and why what the wheel takes from them isn't GPL-only.
# A project that mentions the GPL and isn't listed here fails the build until someone checks it.
REVIEWED_GPL = {
    "dbus": "libdbus is AFL-2.1 OR GPL-2.0-or-later; the GPL-only parts are the daemon and tools",
    "flac": "libFLAC is BSD-3-Clause; the GPL covers the command-line tools",
    "freetype": "FTL OR GPL-2.0-or-later, used under the FTL",
    "gcc": "only libatomic, a runtime library under the GCC Runtime Library Exception, which WebKit links",
    "gnutls": "libgnutls is LGPL-2.1-or-later; the GPL covers the tools and libgnutls-dane's tests",
    "gobject-introspection": "only typelibs are bundled, built from the LGPL and MIT .gir data",
    "hidapi": "BSD-3-Clause OR GPL-3.0-only OR HIDAPI, used under the BSD license",
    "hicolor-icon-theme": "only index.theme, a data file that no code links to",
    "hunspell": "MPL-1.1 OR GPL-2.0-or-later OR LGPL-2.1-or-later, used under the LGPL or the MPL",
    "keyutils": "libkeyutils is LGPL-2.1-or-later; the GPL covers the keyctl tools",
    "libcap": "BSD-3-Clause OR GPL-2.0-only, used under the BSD license",
    "libidn2": "libidn2 is LGPL-3.0-or-later OR GPL-2.0-or-later; the GPL-3.0 parts are the idn2 tool",
    "libsndfile": "libsndfile is LGPL-2.1-or-later; the GPL covers example programs",
    "libtasn1": "libtasn1 is LGPL-2.1-or-later; the GPL covers the asn1 tools",
    "libunistring": "LGPL-3.0-or-later OR GPL-2.0-or-later",
    "lz4": "liblz4 is BSD-2-Clause; the GPL covers the lz4 tool",
    "nettle": "LGPL-3.0-or-later OR GPL-2.0-or-later",
    "systemd": "libsystemd is LGPL-2.1-or-later; the GPL covers some of systemd's programs",
    "vte": "libvte is LGPL-3.0-or-later; the GPL-3.0 files are the vte app and test tools, which aren't built",
    "zstd": "BSD-3-Clause OR GPL-2.0-only, used under the BSD license",
}
GPL = re.compile(r"(?<![L\w])GPL")


@dataclass
class Component:
    name: str
    version: str
    license: str
    origin: str
    sources: list[Path]
    texts: dict[str, bytes]
    files: list[str] = field(default_factory=list)
    parts: list["Component"] = field(default_factory=list)


def license_texts(members, extra=frozenset()):
    """{name: text} for the license files among (path, read) pairs of a source tree."""
    found = {}
    for parts, read in members:
        top_level = len(parts) == 1 and LICENSE_NAME.match(parts[0])
        if top_level or (len(parts) == 2 and parts[0] in ("LICENSES", "licenses")) or "/".join(parts) in extra:
            found["/".join(parts)] = read()
    return found


def tree_texts(directory, extra=frozenset()):
    paths = [*directory.iterdir(), *directory.glob("LICENSES/*"), *(directory / name for name in extra)]
    return license_texts(((path.relative_to(directory).parts, path.read_bytes) for path in paths if path.is_file()),
                         extra)


def archive_texts(data, extra=frozenset()):
    """License files at the top of the source tree in a tar archive."""
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
        members = [(Path(m.name).parts[1:], m) for m in archive.getmembers() if m.isfile()]
        return license_texts(((parts, lambda m=m: archive.extractfile(m).read()) for parts, m in members), extra)


def top_directory(archive):
    with tarfile.open(archive, mode="r|*") as stream:
        return Path(next(iter(stream)).name).parts[0]


def download(url, target, sha256=None):
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url) as response:
            data = response.read()
        if sha256 and hashlib.sha256(data).hexdigest() != sha256:
            raise RuntimeError(f"{url}: checksum mismatch")
        target.write_bytes(data)
    return target


class Attribution:
    def __init__(self, prefix, cache, extra_prefixes=()):
        self.prefix = Path(prefix) if prefix else None
        self.cache = cache
        self.components = {}
        self.owners = {}
        self.archives = None
        if self.prefix:
            # glib-bootstrap installs the files glib installs again, so glib comes later and wins.
            for log in sorted(SOURCE_TREE.glob("build-*/meson-logs/install-log.txt"),
                              key=lambda p: p.parent.parent.name != "build-glib-bootstrap"):
                stamp = log.parent.parent.name.removeprefix("build-")
                for line in log.read_text().splitlines():
                    if not line.startswith("#"):
                        self.owners[line] = ("meson", stamp)
            for name, (_, patterns) in OTHER_BUILDS.items():
                for prefix in [self.prefix, *map(Path, extra_prefixes)]:
                    for pattern in patterns:
                        for path in prefix.glob(pattern):
                            self.owners[str(path)] = ("other", name)
        # Every file of every installed RPM package, to its source RPM and its own package's license. Packages from
        # one source RPM can differ, as libgcrypt-devel adds the GPL of its tools to libgcrypt's LGPL, so a component
        # takes the licenses of the packages whose files the wheel bundles.
        self.rpm_files, self.rpm_licenses = {}, {}
        if shutil.which("rpm"):
            listing = subprocess.run(["rpm", "-qa", "--qf", "[%{FILENAMES}\t%{=SOURCERPM}\t%{=LICENSE}\n]"],
                                     capture_output=True, text=True, check=True).stdout
            for line in listing.splitlines():
                path, source_rpm, license = line.split("\t")
                self.rpm_files[path] = (source_rpm, license)
        self.distributions = {}
        for distribution in metadata.distributions():
            for file in distribution.files or []:
                self.distributions[str(Path(distribution.locate_file(file)).resolve())] = distribution

    # Components, one per project.

    def component(self, key):
        if key not in self.components:
            kind, name = key
            self.components[key] = getattr(self, f"_{kind}")(name)
        return self.components[key]

    def source_archive(self, directory):
        if self.archives is None:
            self.archives = {top_directory(path): path for path in (SOURCE_TREE / "archives").iterdir()}
        return self.archives[directory.name]

    def _meson(self, stamp):
        build = SOURCE_TREE / f"build-{stamp}"
        info = json.loads((build / "meson-info" / "intro-projectinfo.json").read_text())
        source = Path(json.loads((build / "meson-info" / "meson-info.json").read_text())["directories"]["source"])
        declared = " AND ".join(info.get("license") or [])
        # gst-python is built once for each Python version, as gst-python-cp313 and so on.
        name = {"glib-bootstrap": "glib", "harfbuzz-icu": "harfbuzz"}.get(stamp) or re.sub(r"-cp\d+$", "", stamp)
        license = MESON_LICENSES.get(name) or declared
        component = Component(name, info["version"], license, "built from source", [self.source_archive(source)],
                              tree_texts(source, OTHER_TEXTS.get(name, frozenset())))
        if (source / "Cargo.lock").exists():
            component.parts = self.crates(source / "Cargo.lock")
        return component

    def _other(self, name):
        # ICU unpacks to icu/, without its version.
        source = next(p for p in [*SOURCE_TREE.glob(f"{name}-*"), SOURCE_TREE / name] if p.is_dir())
        archive = self.source_archive(source)
        version = re.search(r"\d+(?:\.\d+)+", archive.name).group(0)
        return Component(name, version, OTHER_BUILDS[name][0], "built from source", [archive],
                         tree_texts(source, OTHER_TEXTS.get(name, frozenset())))

    def crates(self, lock):
        """The crates.io packages a Rust project compiled in: those cargo downloaded for it."""
        registry = Path.home() / ".cargo" / "registry"
        found = []
        for package in tomllib.loads(lock.read_text()).get("package", []):
            if not package.get("source", "").startswith("registry+"):
                continue
            name, version = package["name"], package["version"]
            crate = next(registry.glob(f"cache/*/{name}-{version}.crate"), None)
            if not crate:
                continue
            source = next(registry.glob(f"src/*/{name}-{version}"))
            manifest = tomllib.loads((source / "Cargo.toml").read_text())["package"]
            license = manifest.get("license", "").replace("/", " OR ")
            texts = tree_texts(source)
            if not texts:
                # The crate ships no license file, so give the standard text of what it declares.
                authors = ", ".join(manifest.get("authors", [])) or f"the {name} authors"
                header = f"{name} {version} declares the license {license} and includes no license file.\n" \
                         f"Copyright the {name} authors: {authors}\n\n".encode()
                for spdx in re.findall(r"[\w.-]+", license.replace(" OR ", " ").replace(" AND ", " ")):
                    texts[f"{spdx}.txt"] = header + (TEXTS / f"{spdx}.txt").read_bytes()
            found.append(Component(name, version, license, "Rust crate from crates.io", [crate], texts))
        return found

    def _rpm(self, source_rpm):
        name, version, _ = source_rpm.removesuffix(".src.rpm").rsplit("-", 2)
        target = self.cache / "srpms" / source_rpm
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["dnf", "-q", "download", "--source", "--enablerepo=*-source", "--destdir", str(target.parent),
                            source_rpm.removesuffix(".src.rpm")], check=True)
        payload = subprocess.run(["rpm2archive", "-n", "-"], stdin=target.open("rb"), capture_output=True,
                                 check=True).stdout
        texts = {}
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:") as srpm:
            for member in srpm.getmembers():
                base = Path(member.name).name
                if not member.isfile():
                    continue
                if LICENSE_NAME.match(base):
                    texts[base] = srpm.extractfile(member).read()
                elif ARCHIVE.search(base):
                    texts.update(archive_texts(srpm.extractfile(member).read(), OTHER_TEXTS.get(name, frozenset())))
        if not texts and name in STAND_IN_TEXTS:
            texts[STAND_IN_TEXTS[name]] = (TEXTS / STAND_IN_TEXTS[name]).read_bytes()
        license = " AND ".join(sorted(self.rpm_licenses[source_rpm]))
        return Component(name, version, license, "AlmaLinux 9 package", [target], texts)

    def _dpkg(self, package):
        source, version = subprocess.run(["dpkg-query", "-W", "-f", "${source:Package}\t${Version}", package],
                                         capture_output=True, text=True, check=True).stdout.split("\t")
        copyright_file = Path("/usr/share/doc") / package.split(":")[0] / "copyright"
        texts = {"copyright": copyright_file.read_bytes()} if copyright_file.exists() else {}
        return Component(source, version, "see copyright", "Debian package", [], texts)

    def _python(self, name):
        distribution = metadata.distribution(name)
        version = distribution.version
        release = json.load(urllib.request.urlopen(f"https://pypi.org/pypi/{name}/{version}/json"))
        sdist = next(u for u in release["urls"] if u["packagetype"] == "sdist")
        archive = download(sdist["url"], self.cache / "sdists" / sdist["filename"], sdist["digests"]["sha256"])
        # Some releases put the whole license text in the License field, so fall back to the classifiers then.
        info = release["info"]
        license = info.get("license_expression") or (info.get("license") or "").strip()
        if "\n" in license or not license:
            license = " AND ".join(c.split(" :: ")[-1] for c in info["classifiers"] if c.startswith("License ::"))
        return Component(name, version, license, "Python package from PyPI", [archive],
                         archive_texts(archive.read_bytes()))

    # Files.

    def owner_keys(self, sources):
        """The component key for each source file, or None when nothing claims it."""
        keys, unclaimed = {}, []
        for source in sources:
            resolved = str(source.resolve())
            key = self.owners.get(str(source)) or self.owners.get(resolved)
            if not key and resolved in self.distributions:
                key = ("python", self.distributions[resolved].metadata["Name"])
            keys[source] = key
            if not key:
                unclaimed.append(source)
        if self.rpm_files and unclaimed:
            for source in unclaimed:
                found = self.rpm_files.get(str(source)) or self.rpm_files.get(str(source.resolve()))
                if found:
                    keys[source] = ("rpm", found[0])
                    self.rpm_licenses.setdefault(found[0], set()).add(found[1])
        if shutil.which("dpkg-query") and not self.rpm_files and unclaimed:
            # Debian's file lists name /usr/lib files both with and without the /usr of merged /usr.
            candidates = {source: {str(source), str(source.resolve()), str(source.resolve()).removeprefix("/usr")}
                          for source in unclaimed}
            owned = {}
            names = sorted(set().union(*candidates.values()))
            for chunk in range(0, len(names), 500):
                output = subprocess.run(["dpkg-query", "-S", *names[chunk:chunk + 500]], capture_output=True,
                                        text=True).stdout
                for line in output.splitlines():
                    packages, _, path = line.partition(": ")
                    owned[path] = packages.split(",")[0].strip()
            for source, names in candidates.items():
                package = next((owned[name] for name in names if name in owned), None)
                if package:
                    keys[source] = ("dpkg", package)
        return keys

    def attribute(self, origins):
        """Components with their bundled files, from {bundled path: source file}. Raises on a gap."""
        keys = self.owner_keys(sorted(set(origins.values())))
        gaps = sorted(bundled for bundled, source in origins.items() if not keys[source])
        if gaps:
            raise RuntimeError("no project is known for these bundled files:\n  " + "\n  ".join(gaps))
        used = {}
        for bundled, source in sorted(origins.items()):
            component = self.component(keys[source])
            used[id(component)] = component
            component.files.append(bundled)
        components = sorted(used.values(), key=lambda c: c.name.lower())
        missing = [c.name for c in components for c in [c, *c.parts] if not c.texts]
        if missing:
            raise RuntimeError(f"no license texts were found for {', '.join(missing)}")
        unreviewed = [f"{c.name} ({c.license})" for c in components for c in [c, *c.parts]
                      if GPL.search(c.license) and c.name not in REVIEWED_GPL]
        if unreviewed:
            raise RuntimeError("these projects mention the GPL; check that what the wheel takes from them isn't "
                               "GPL-only, then add them to REVIEWED_GPL:\n  " + "\n  ".join(unreviewed))
        return components


def folder(component):
    return re.sub(r"[^\w.+-]", "_", component.name)


def write_notices(components, target):
    """Write each component's license texts and NOTICES.txt, which lists them all."""
    target.mkdir(parents=True)
    lines = ["PyLiite4 bundles the projects below. Each project's license texts are in the folder of",
             "the same name next to this file, and components.json lists every bundled file by project.",
             "The source archive of each exact version is published with each PyLiite4 release.", ""]

    def entry(component, directory, indent=""):
        for name, text in component.texts.items():
            path = directory / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(text)
        lines.extend([f"{indent}{component.name} {component.version}",
                      f"{indent}  License: {component.license or 'see the license texts'}",
                      f"{indent}  Origin: {component.origin}",
                      *([f"{indent}  Note: {REVIEWED_GPL[component.name]}"]
                        if GPL.search(component.license) and component.name in REVIEWED_GPL else []),
                      f"{indent}  Source: {', '.join(s.name for s in component.sources) or 'the distribution archive'}",
                      f"{indent}  Licenses: {directory.relative_to(target)}/"])
        if component.files:
            lines.append(f"{indent}  Bundled files: {len(component.files)}, including {component.files[0]}")
        if component.parts:
            lines.append(f"{indent}  Compiled in from {len(component.parts)} Rust crates:")
        lines.append("")
        for part in component.parts:
            entry(part, directory / "crates" / f"{part.name}-{part.version}", indent + "    ")

    for component in components:
        entry(component, target / folder(component))
    (target / "NOTICES.txt").write_text("\n".join(lines))

    def record(component):
        return {"name": component.name, "version": component.version, "license": component.license,
                "origin": component.origin, "sources": [s.name for s in component.sources],
                "files": component.files, "crates": [record(part) for part in component.parts]}

    (target / "components.json").write_text(json.dumps([record(c) for c in components], indent=1) + "\n")


def collect_sources(components, target):
    """Copy the source archive of every component, and their checksums, into ``target``."""
    target.mkdir(parents=True, exist_ok=True)
    every = [part for component in components for part in [component, *component.parts]]
    for source in sorted({source for component in every for source in component.sources}):
        if not (target / source.name).exists():
            shutil.copy(source, target)
    sums = [f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}"
            for path in sorted(target.iterdir()) if path.name != "SHA256SUMS"]
    (target / "SHA256SUMS").write_text("\n".join(sums) + "\n")
