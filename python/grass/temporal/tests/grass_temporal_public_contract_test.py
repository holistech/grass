"""Pin the names, module paths and methods that code outside the library uses

The data file lists everything that the repository (tools, GUI, scripts, tests
of other packages) and the OSGeo grass-addons use from grass.temporal, with the
origin ("repo", "addons" or "addons+repo") of each entry. It was measured on
2026-10-25 by a read-only AST scan of both trees. Methods and members are an
upper bound: every attribute name seen outside that a class (or the object
behind an instance attribute such as metadata) has today is listed, because
the scan cannot tell which object a name was called on.

A failure names the origin: an entry from "addons" is a break for code the
repository cannot fix; an entry from "repo" only needs its caller changed in
the same commit.
"""

import importlib
import json
from pathlib import Path

import grass.temporal as tgis

CONTRACT = json.loads(
    Path(__file__).with_name("data").joinpath("public_contract.json").read_text()
)


def _report(missing):
    return "\n".join(f"{what} (used by {origin})" for what, origin in missing)


def test_top_names_resolve():
    missing = [
        (f"grass.temporal.{name}", origin)
        for name, origin in CONTRACT["top_names"].items()
        if not hasattr(tgis, name)
    ]
    assert not missing, _report(missing)


def test_module_paths_import():
    missing = []
    for module, entry in CONTRACT["module_paths"].items():
        try:
            imported = importlib.import_module(module)
        except ImportError:
            missing.append((module, entry["origins"]))
            continue
        missing.extend(
            (f"{module}.{name}", origin)
            for name, origin in entry["names"].items()
            if not hasattr(imported, name)
        )
    assert not missing, _report(missing)


def test_module_attributes():
    missing = [
        (f"grass.temporal.{name}", origin)
        for name, origin in CONTRACT["module_attributes"].items()
        if not hasattr(tgis, name) or not hasattr(getattr(tgis, name), "__name__")
    ]
    assert not missing, _report(missing)


def test_methods_exist():
    missing = []
    for class_name, methods in CONTRACT["methods"].items():
        cls = getattr(tgis, class_name, None)
        if cls is None:
            missing.append((f"grass.temporal.{class_name}", "all its methods"))
            continue
        missing.extend(
            (f"{class_name}.{name}", origin)
            for name, origin in methods.items()
            if not hasattr(cls, name)
        )
    assert not missing, _report(missing)


def test_instance_attributes_exist():
    missing = []
    for class_name, attributes in CONTRACT["attributes"].items():
        obj = getattr(tgis, class_name)("contract@test")
        missing.extend(
            (f"{class_name}().{name}", origin)
            for name, origin in attributes.items()
            if not hasattr(obj, name)
        )
    assert not missing, _report(missing)


def test_member_methods_exist():
    # Code outside calls e.g. map.metadata.get_min(); the classes behind
    # these attributes are part of the interface although they are not exported.
    missing = []
    for path, members in CONTRACT["members"].items():
        class_name, attribute = path.split(".")
        member = getattr(getattr(tgis, class_name)("contract@test"), attribute, None)
        missing.extend(
            (f"{class_name}().{attribute}.{name}", origin)
            for name, origin in members.items()
            if not hasattr(member, name)
        )
    assert not missing, _report(missing)


def test_contract_is_not_empty():
    # A measurement that returned nothing would make every test above pass.
    assert len(CONTRACT["top_names"]) > 50
    assert len(CONTRACT["methods"]) > 10
    assert len(CONTRACT["attributes"]) == 6
    assert sum(len(v) for v in CONTRACT["members"].values()) > 300
    assert any("addons" in o for o in CONTRACT["top_names"].values())
