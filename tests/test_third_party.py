"""The source notices should tell someone where to get the listed archives."""

import json
from pathlib import Path

import pytest

third_party = pytest.importorskip("tools.third_party", reason="needs the source checkout's build tools")


def test_notices_link_the_matching_release_and_keep_component_details(tmp_path):
    crate = third_party.Component("sample-crate", "2.0", "MIT", "Rust crate from crates.io",
                                  [Path("sample-crate-2.0.crate")], {"LICENSE": b"crate license"})
    component = third_party.Component("sample", "1.2", "MIT", "built from source",
                                      [Path("sample-1.2.tar.xz")], {"LICENSE": b"project license"},
                                      files=["lib/libsample.so"], parts=[crate])
    target = tmp_path / "licenses"
    third_party.write_notices([component], target, "0.2.0")

    notices = (target / "NOTICES.txt").read_text()
    assert "https://github.com/supersolvers/PyLiite4/releases/tag/v0.2.0" in notices
    assert "SHA256SUMS" in notices
    assert "filenames below identify the exact archives to download" in notices
    assert "GitHub's automatic Source code downloads" in notices
    assert "source bundle" not in notices
    assert "unreleased" not in notices
    assert "Source: sample-1.2.tar.xz" in notices
    assert "Source: sample-crate-2.0.crate" in notices
    assert (target / "sample" / "LICENSE").read_bytes() == b"project license"
    assert (target / "sample" / "crates" / "sample-crate-2.0" / "LICENSE").read_bytes() == b"crate license"
    records = json.loads((target / "components.json").read_text())
    assert records[0]["sources"] == ["sample-1.2.tar.xz"]
    assert records[0]["crates"][0]["sources"] == ["sample-crate-2.0.crate"]


def test_release_tag_encodes_version_characters():
    assert "/releases/tag/v0.2.0%2Blocal" in third_party.notices_header("0.2.0+local")
