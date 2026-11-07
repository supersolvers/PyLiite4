"""The Python range should describe the project; wheel tags select the ABI."""

import importlib
import zipfile
from email.parser import BytesParser
from pathlib import Path
from types import SimpleNamespace

import pytest
from packaging.specifiers import SpecifierSet


@pytest.mark.parametrize("minor", range(10, 15))
@pytest.mark.parametrize("name,bundle", [("PyLiite4", "_bundled"),
                                        ("PyLiite4-Addons", "_addons"),
                                        ("PyLiite4-Poppler", "_poppler")])
def test_python_range_does_not_depend_on_build_interpreter(tmp_path, monkeypatch, minor, name, bundle):
    tools = Path(__file__).resolve().parent.parent / "tools"
    if not (tools / "build_wheel.py").exists():
        pytest.skip("needs the source checkout's wheel builder")
    monkeypatch.syspath_prepend(str(tools))
    builder = importlib.import_module("build_wheel")
    project = builder.tomllib.loads((builder.ROOT / "pyproject.toml").read_text())["project"]
    monkeypatch.setattr(builder, "sys", SimpleNamespace(version_info=SimpleNamespace(major=3, minor=minor)))
    monkeypatch.setattr(builder, "glibc_tag", lambda: "manylinux_2_34_x86_64")

    package = tmp_path / "PyLiite4"
    licenses = package / bundle / "licenses"
    licenses.mkdir(parents=True)
    (licenses / "NOTICES.txt").write_text("Fixture source notices\n")
    wheel = builder.build_wheel(package, tmp_path / "dist", name=name, bundle=bundle, entry_points=False)

    assert f"-cp3{minor}-cp3{minor}-" in wheel.name
    with zipfile.ZipFile(wheel) as archive:
        metadata_name = next(path for path in archive.namelist() if path.endswith(".dist-info/METADATA"))
        metadata = BytesParser().parsebytes(archive.read(metadata_name))
    assert metadata["Requires-Python"] == project["requires-python"]
    accepted = SpecifierSet(metadata["Requires-Python"])
    assert all(f"3.{version}" in accepted for version in range(10, 15))
    assert "3.9" not in accepted
