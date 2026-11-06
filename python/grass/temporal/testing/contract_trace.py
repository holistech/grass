# SPDX-FileCopyrightText: 2026 Soeren Gebbert
# SPDX-FileCopyrightText: GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later

"""Trace which public functions of grass.temporal an example script calls

The documentation shows scripts that use ``grass.temporal``. The public
contract (``tests/data/public_contract.json``) lists what code outside the
library may rely on, so a script of the documentation is only allowed to call
what the contract lists. ``called_names`` runs a script and records the calls,
``missing_from_contract`` names the calls the contract does not cover.

The calls are recorded with ``sys.setprofile`` while the script runs, not read
from its source. Which class an attribute access such as ``stds.metadata.get_min``
reaches cannot be resolved statically, and the profiler reports the code that
really ran. A call is reported under the module and class that define the
function, so a method inherited from a base class is reported under the base
class; ``missing_from_contract`` accepts it when the contract lists the method
for any class that inherits from that base.

Only calls made by the script itself count, not those that the library makes
on its own behalf: the script may use what the contract lists, and the library
calls whatever it needs. Only functions of ``grass.temporal`` count. The helpers of
``grass.temporal.testing`` and every name with a component that starts with an
underscore (private functions, ``__init__``) are left out, as are the inner
functions and comprehensions of a public function, which are not part of the
interface. Calls made before the script starts, such as the import of the
package, are not recorded. A script that starts threads or other Python processes is
traced only in its main thread.

This module must not import pytest; fixtures belong in conftest.py files.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from functools import cache
from pathlib import Path

PACKAGE = "grass.temporal"
CONTRACT_ENV = "GRASS_TEMPORAL_PUBLIC_CONTRACT"
CONTRACT_PATH = Path("python/grass/temporal/tests/data/public_contract.json")

# The child imports this module, hence grass.temporal, before the hook is set,
# so the import of the package does not show up in the result.
_CHILD = "from grass.temporal.testing.contract_trace import run_traced; run_traced()"


def called_names(script: Path, *, env: dict, cwd: Path) -> set[str]:
    """Run ``python3 <script>`` and return the grass.temporal names it called

    A name is ``grass.temporal.<module>.<function>`` or
    ``grass.temporal.<module>.<Class>.<method>``, with the module and class
    that define the code.

    The trace is a floor, not a proof. Only calls of functions and methods
    show: a constructor (``__init__`` is private), a plain attribute read, a
    constant and a call made through a thread leave no name, so this check
    does not replace reading the example. A property whose getter has a name of
    its own is reported under the getter (``get_temporal_extent``, not
    ``temporal_extent``), because the profiler sees the getter's code.

    :param script: The Python file to run
    :param env: The environment of the child process; it must let the child
                import grass.temporal and, for a script that needs one, hold
                the GRASS session variables
    :param cwd: The working directory of the child process
    :raises RuntimeError: If the script ends with a return code other than 0;
                          the message holds its stderr
    """
    with tempfile.TemporaryDirectory() as folder:
        result_file = Path(folder) / "names.json"
        result = subprocess.run(
            [sys.executable, "-c", _CHILD, str(script), str(result_file)],
            env=env,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            msg = f"{script} ended with {result.returncode}:\n{result.stderr}"
            raise RuntimeError(msg)
        return set(json.loads(result_file.read_text()))


def _generated_accessor(frame) -> str | None:
    """The name of a get_/set_/property accessor that the metadata rows generate

    rows._generate_accessors() builds one getter and one setter code object and
    closes each over the column. co_qualname of such a frame says nothing
    useful, so the function is found again in the class of ``self``: the entry
    that has this code object and the same closed-over values.
    """
    code = frame.f_code
    owner = frame.f_locals.get("self")
    if owner is None or not code.co_filename.endswith("rows.py"):
        return None
    wanted = {name: frame.f_locals.get(name) for name in code.co_freevars}
    for base in type(owner).__mro__:
        for attribute, entry in vars(base).items():
            for function in (
                entry,
                getattr(entry, "fget", None),
                getattr(entry, "fset", None),
            ):
                if (
                    getattr(function, "__code__", None) is not code
                    or not function.__closure__
                ):
                    continue
                closed = dict(
                    zip(
                        code.co_freevars,
                        (cell.cell_contents for cell in function.__closure__),
                        strict=True,
                    )
                )
                if closed == wanted and not attribute.startswith("_"):
                    return f"{base.__module__}.{base.__qualname__}.{attribute}"
    return None


def run_traced() -> None:
    """Run the script of ``sys.argv[1]`` under the profile hook (child side)

    ``sys.argv[2]`` names the file that receives the recorded names as JSON.
    The names are written also when the script fails, so that the cause of a
    failure is not hidden behind a missing file.
    """
    import runpy

    script, result_file = sys.argv[1], sys.argv[2]
    names: set[str] = set()
    decided: dict = {}

    def called_by_script(frame):
        # Standard library frames (contextlib, threading, functools) may sit
        # between the script and the callee, so look for the nearest frame
        # that is the script or the library. A thread of the library has none.
        caller = frame.f_back
        while caller is not None:
            owner = caller.f_globals.get("__name__", "")
            if owner == "__main__":
                return True
            if owner.startswith(PACKAGE):
                return False
            caller = caller.f_back
        return False

    def name_of(code, module):
        testing = f"{PACKAGE}.testing"
        if not module.startswith(f"{PACKAGE}.") or (
            module == testing or module.startswith(f"{testing}.")
        ):
            return None
        parts = [*module.split("."), *code.co_qualname.split(".")]
        if any(part.startswith("_") or "<" in part for part in parts):
            return None
        return ".".join(parts)

    def hook(frame, event, _arg):
        if event != "call":
            return
        if not called_by_script(frame):
            return
        code = frame.f_code
        module = frame.f_globals.get("__name__", "")
        if "<locals>" in code.co_qualname:
            name = _generated_accessor(frame)
        else:
            key = (code, module)
            if key not in decided:
                decided[key] = name_of(code, module)
            name = decided[key]
        if name:
            names.add(name)

    # Run the script as python3 <script> would: its folder leads sys.path.
    sys.path[0] = str(Path(script).resolve().parent)
    sys.argv = [script]
    try:
        sys.setprofile(hook)
        try:
            runpy.run_path(script, run_name="__main__")
        finally:
            sys.setprofile(None)
    finally:
        Path(result_file).write_text(json.dumps(sorted(names)))


def _find_contract_file() -> Path:
    """The contract file: the environment variable, else the source tree

    The tests of the library run against the installed copy of the package,
    which does not hold the tests, so the file is searched from the working
    directory upwards.
    """
    if os.environ.get(CONTRACT_ENV):
        return Path(os.environ[CONTRACT_ENV])
    here = Path.cwd().resolve()
    for folder in (here, *here.parents):
        if (folder / CONTRACT_PATH).is_file():
            return folder / CONTRACT_PATH
    msg = (
        f"Cannot find {CONTRACT_PATH} above {here}; "
        f"run from the source tree or set {CONTRACT_ENV}"
    )
    raise FileNotFoundError(msg)


# Classes whose methods the contract lists although code outside reaches them
# through other objects (a map's spatial_extent, a dataset's temporal_extent)
# and does not import them: the package does not export them. The module that
# defines each is named here, once, for the contract test and the trace.
MODULE_OF_UNEXPORTED_CLASS = {
    "AbstractDataset": "abstract_dataset",
    "AbstractMapDataset": "abstract_map_dataset",
    "CLibrariesInterface": "c_libraries_interface",
    "SpatialExtent": "spatial_extent",
    "TemporalExtent": "temporal_extent",
}


def class_named(name: str):
    """The class of a contract entry, exported or from its module"""
    import grass.temporal as tgis

    if hasattr(tgis, name):
        return getattr(tgis, name)
    module = importlib.import_module(f"{PACKAGE}.{MODULE_OF_UNEXPORTED_CLASS[name]}")
    return getattr(module, name)


def _qualified(cls, name: str) -> str:
    return f"{cls.__module__}.{cls.__qualname__}.{name}"


def _allow(allowed: set[str], cls, names) -> None:
    """Allow each name for the class and for every base class of it"""
    for base in cls.__mro__:
        if base.__module__.startswith(f"{PACKAGE}."):
            allowed.update(_qualified(base, name) for name in names)


@cache
def _allowed_methods(contract_text: str) -> frozenset[str]:
    """The qualified methods that the contract allows, bases included

    ``methods`` lists the methods of a class, ``attributes`` the attributes of
    an instance (a property runs code when it is read) and ``members`` the
    methods of the object behind an instance attribute such as ``metadata``.
    """
    contract = json.loads(contract_text)
    allowed: set[str] = set()
    for class_name, names in {**contract["methods"], **contract["attributes"]}.items():
        _allow(allowed, class_named(class_name), names)
    for path, names in contract["members"].items():
        class_name, attribute = path.split(".")
        # The datasets build their rows without a database, so this needs no
        # session (checked on 2026-11-06 in a process that never called init()).
        member = getattr(class_named(class_name)("contract@trace"), attribute)
        _allow(allowed, type(member), names)
    return frozenset(allowed)


def _split(name: str) -> tuple[str, list[str]]:
    """Split a qualified name into its module and the qualname behind it"""
    parts = name.split(".")
    end = len(PACKAGE.split("."))
    module = ".".join(parts[:end])
    # Extend the module as long as the next part is a module of the package.
    # find_spec() fails for a submodule of a plain module (a class of it).
    while end < len(parts) - 1:
        try:
            found = importlib.util.find_spec(f"{module}.{parts[end]}")
        except (ModuleNotFoundError, AttributeError):
            break
        if found is None:
            break
        module = f"{module}.{parts[end]}"
        end += 1
    return module, parts[end:]


@cache
def _modules_of_exports() -> dict[str, str]:
    """The module that grass/temporal/__init__.py imports each name from

    The source is read, not the namespace: a test session may replace a
    function of the package by a wrapper, and the wrapper has another
    __module__ than the code that ran.
    """
    import ast

    import grass.temporal as tgis

    tree = ast.parse(Path(tgis.__file__).read_text())
    modules = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
            for alias in node.names:
                modules[alias.asname or alias.name] = f"{PACKAGE}.{node.module}"
    return modules


def _is_top_name(function: str, module: str, contract: dict) -> bool:
    """Tell whether the contract's top name is this very function

    A bare name match would let a copy of the same name elsewhere in the
    package pass (classic.granularity keeps its own copies of functions), so
    the module that grass.temporal imports the name from must be the module
    that defines the called code.
    """
    return (
        function in contract["top_names"]
        and _modules_of_exports().get(function) == module
    )


def missing_from_contract(
    names: set[str], *, contract: dict | None = None
) -> list[str]:
    """The names that the public contract does not cover, sorted

    A function is covered if it is a ``top_names`` entry or a name of a
    ``module_paths`` entry whose module is, or contains, the module that
    defines it. A method is covered if the contract lists it for its class or
    for a class that inherits from it, or as a member behind an instance
    attribute (see ``_allowed_methods``). The ``module_attributes`` entries
    pin the modules themselves, not the names in them, so a function reached as
    ``tgis.core.name`` needs its own ``module_paths`` entry.

    :param names: The result of called_names()
    :param contract: The contract as a dictionary, by default the file in the
                     source tree
    """
    if contract is None:
        contract = json.loads(_find_contract_file().read_text())
    contract_text = json.dumps(contract, sort_keys=True)
    missing = []
    for name in names:
        module, qualname = _split(name)
        if len(qualname) == 1:
            function = qualname[0]
            covered = _is_top_name(function, module, contract) or any(
                function in entry["names"]
                and (module == path or module.startswith(f"{path}."))
                for path, entry in contract["module_paths"].items()
            )
        else:
            covered = name in _allowed_methods(contract_text)
        if not covered:
            missing.append(name)
    return sorted(missing)
