# SPDX-FileCopyrightText: 2026 Soeren Gebbert
# SPDX-FileCopyrightText: GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later

"""Find the North Carolina sample dataset and see whether a run changed it

The examples of the temporal manuals run in the North Carolina sample dataset
``nc_spm_08_grass7``, as the reader does. The tests do not download it. Whoever
runs them unpacks it and names the folder in the environment variable
``GRASS_TEMPORAL_TEST_NC_SPM``; without the variable, ``~/grassdata/nc_spm_08_grass7``
and then ``~/grassdata/nc_spm_full_v2beta1`` are taken, the second because the
upstream CI downloads that version. A test that needs the dataset and finds none
fails; it is not skipped, so that a missing dataset never passes unseen.

The examples never run in the dataset itself. ``project_in_dataset`` makes a
project whose ``PERMANENT`` is a link to the one of the dataset, so the maps
of the reader are there and every new mapset is in a temporary directory.
``snapshot`` records every file of ``PERMANENT`` with size and time, to show
that a run wrote nothing through the link. ``fingerprint`` holds the content
of the data the examples may use; it is the same in both versions of the
dataset (``USED_DATA``), so a manual shows the same output with either.

This module must not import pytest; fixtures belong in conftest.py files.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
from pathlib import Path

from grass.grassdb.checks import is_location_valid
from grass.temporal.db import sql_statement

VARIABLE = "GRASS_TEMPORAL_TEST_NC_SPM"
DOWNLOAD = "https://grass.osgeo.org/sampledata/north_carolina/nc_spm_08_grass7.zip"
# The name of the project as the reader unpacks it. The test project carries
# it too, so the outputs that name the project need no normalisation.
PROJECT_NAME = "nc_spm_08_grass7"
# The folders below ~/grassdata that are taken without the variable, in order.
DEFAULT_NAMES = (PROJECT_NAME, "nc_spm_full_v2beta1")

# The data that the examples may use. Each is in both versions of the dataset.
RASTERS = ("elev_state_500m", "ncmask_500m")
# Each vector keeps its attributes in the table of its own name (see the dbln
# files, which are part of the fingerprint).
VECTORS = (
    "boundary_county",
    "geonames_NC",
    "nc_state",
    "precip_30ynormals",
    "usgsgages",
)
# The files of the project that the region and the coordinate system come
# from. PROJ_EPSG of nc_spm_08_grass7 and PROJ_SRID with PROJ_WKT of
# nc_spm_full_v2beta1 name the same EPSG:3358 in two forms, so they are left
# out; an example that prints them would differ between the versions.
PROJECT_FILES = ("DEFAULT_WIND", "PROJ_INFO", "PROJ_UNITS")
_RASTER_ELEMENTS = ("cats", "cell", "cellhd", "colr", "fcell", "hist")

# The sha256 of each file that fingerprint() reads, by its path below
# PERMANENT, and of each table ("table:<name>"). Recorded 2026-11-03 with
# fingerprint() from nc_spm_08_grass7 (the zip of DOWNLOAD, sha256
# 9b422564fa7255c8d551f2161d58b97978cd8b4aa94c3f7163cd95af27b609b5) and found
# equal for nc_spm_full_v2beta1; the tables were also compared with the .dump
# of the sqlite3 shell, equal in both.
USED_DATA: dict[str, str] = {
    "DEFAULT_WIND": "35b0f2c7087414adcf0cd2f7f8de19f6a2bbebbcca4a444373a342936a9e6b80",
    "PROJ_INFO": "264fe4f80ed7bde940d2b3961119778f9220e570714b48393be9a72c9ed6b537",
    "PROJ_UNITS": "d2f4b3a18acf3f4ce032cd5600b76dad31cd4697783c35785d9464eba2da7d31",
    "cats/elev_state_500m": (
        "a9b6cd6af66acc0a0e047fb9b4defd1580a98a44d339edc2f502e39a9482c4eb"
    ),
    "cats/ncmask_500m": (
        "dfc833d218cf7495f852c34bd1e6fac8cf2444cb83092fe762a9ec11f8b04b5b"
    ),
    "cell/elev_state_500m": (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    ),
    "cell/ncmask_500m": (
        "38ef3fda9c679f6e7d592022373dec0f55ac44dec80673e667ddc5e07abe0b25"
    ),
    "cell_misc/elev_state_500m/f_format": (
        "4dc5a609677b69ca5672e6aadafb6d1214d781062ae3c2430385fa4814165456"
    ),
    "cell_misc/elev_state_500m/f_quant": (
        "a97b0931730e83fbf9284ff00a4c5f7a4eef2189dddb89319a6dfa5871e28923"
    ),
    "cell_misc/elev_state_500m/f_range": (
        "5930fd856464a75b59bd15249809349c0e1e0780b01784fa3d3889727a0b062d"
    ),
    "cell_misc/elev_state_500m/null": (
        "7ad6336e0b83145f623ae9d33b782edfc55a65368a3c5cdac89dc0db33d2243d"
    ),
    "cell_misc/ncmask_500m/null": (
        "ea1266b90f502386d32a6f465e54ba51d2b801e6c3470804461ae24292c543ad"
    ),
    "cell_misc/ncmask_500m/range": (
        "3f11ad6bbc7ecca0b2416b713dee77f1a635c00aaeaa946e14cde1c2bfae56d5"
    ),
    "cellhd/elev_state_500m": (
        "8f5e4c74d988a21761229530cd9596e4264a6d3edb0b3b1f646e4c9536f8de09"
    ),
    "cellhd/ncmask_500m": (
        "5281631a99568426f9521012bceb04561de29e9732c3e1e4e4313126bbe85dfd"
    ),
    "colr/elev_state_500m": (
        "cc8b9cd36a12341b080224ff646e3381d673510fa472228e85af53ba5f3fba20"
    ),
    "fcell/elev_state_500m": (
        "8a19b7a71b36059063981579a50096d3952710ac9e856d467e0a7240ea17484a"
    ),
    "hist/elev_state_500m": (
        "51298d14ba8a67556fa39d0bb7bdcd8c4a4ae6dbef728461f00ccb016565a506"
    ),
    "hist/ncmask_500m": (
        "418730cb27b5e67cb37098d140482d50865de6fd74835aa0b89d569b6d2b4960"
    ),
    "table:boundary_county": (
        "6e9240db91e2dedcca385efea801d8e828b0857eed9694d0772e0f17d4f76958"
    ),
    "table:geonames_NC": (
        "a5d91f5a2ed811016722a9cedb5b6c2eff23aa1420378d8c6375faab9e7bcf29"
    ),
    "table:nc_state": (
        "00309606e412863d698e4a0fa587ecd852ddb3dfd5be27bf15baf219d33effdc"
    ),
    "table:precip_30ynormals": (
        "8f76756a3713947a036b3ee0c79c1822937bd95e63517ecb59fe0a3c507196a0"
    ),
    "table:usgsgages": (
        "c5178a4c9678ed864571c06f2119dee156f1b186ced1f5e6a8cae52db650953c"
    ),
    "vector/boundary_county/cidx": (
        "5ab257e4096b31e4534a6178bc0fff16858be7cd6ded13e99eb6d1c7b5535f8e"
    ),
    "vector/boundary_county/coor": (
        "39426ff4cd7b817f43c25042a521d6b38bce084229c0dc6e1f86709c898575e7"
    ),
    "vector/boundary_county/dbln": (
        "1b04f9445af59b4a4c8b716422d128fff1f28bc1ad1353e05e39cca532ee0913"
    ),
    "vector/boundary_county/head": (
        "58ec996594932c81be22f968ba05ce5ac8c20b9278a1f61a1608046d851747a9"
    ),
    "vector/boundary_county/hist": (
        "5ebb20218f36829e78c1a37d3fca510fcc03e6e0e6272b6209334c245a24dad6"
    ),
    "vector/boundary_county/sidx": (
        "2c4a92d6845d5afb44ff86e34c48c96ac09f79657047a871833a9c4c4db99a18"
    ),
    "vector/boundary_county/topo": (
        "818fc456fd6ef104a76d3fd756327937565a3ac55be08432ce6f746e2f1a9bff"
    ),
    "vector/geonames_NC/cidx": (
        "3fb9675ca759ec30d38bb87985997fdfc1c258b71c7d374460b71c69fe3c2e83"
    ),
    "vector/geonames_NC/coor": (
        "70c1f6fc15feab7d44679ce1bc47925ef9ea021ac2e43b8b5adc14a65f90704b"
    ),
    "vector/geonames_NC/dbln": (
        "1b74cc06bea9d9aa7de4fcff3defbb64c418122451053db694a9c384a19bb03f"
    ),
    "vector/geonames_NC/head": (
        "07b19506aa7a682018c7f3d901a9944e128ec5724e414155635032d8cbe17dfe"
    ),
    "vector/geonames_NC/hist": (
        "b7e1377c05bde982812ec8a18b58aadc5b6ff687615a6f71e9c8e86a78d71403"
    ),
    "vector/geonames_NC/sidx": (
        "2271184d40962e3e8b2a8ac80acbc1d184b6a6238f4d6cbc4d824c1984fef644"
    ),
    "vector/geonames_NC/topo": (
        "21aec958f61583939a43f8a6896a7956a3f40ab2c1634841fa1685546b0248a4"
    ),
    "vector/nc_state/cidx": (
        "f5081454e96f6a5abf95cc14d5aefa33f6d4567cc527461ddbdd3c405fb430d5"
    ),
    "vector/nc_state/coor": (
        "75e72cb51e6b4b12d21cb7ff0a42ecf33a1e8f9de028778b19155c14290ca0fd"
    ),
    "vector/nc_state/dbln": (
        "cf3bf90f59a72a4ceec9296c54421166566e3baff15f782bde34655ad566a182"
    ),
    "vector/nc_state/head": (
        "fff9b557c09f58e2babb49b6cc6e2f32d86dd16d77a9e9caebc9b8e38835e59e"
    ),
    "vector/nc_state/hist": (
        "38d8cf79d489babc6ac41902fc9eab92d9595530a180a635e03ef67db81b16fe"
    ),
    "vector/nc_state/sidx": (
        "dc238e466ea1d73a6ecae1e3318309f07222fc9bebb5206bc4d06544706d92ae"
    ),
    "vector/nc_state/topo": (
        "4c885f50df45a62436ad5826c6d67e2adac99a09b7008cc0428ac055356e00f2"
    ),
    "vector/precip_30ynormals/cidx": (
        "563717177f92a98d1bdae8253908aba883053603eb82c48da2a63e19560f3df3"
    ),
    "vector/precip_30ynormals/coor": (
        "be47fb910b2a3317407b18f0d27821000c5cfbc29425d6ccc2d64d4352d57598"
    ),
    "vector/precip_30ynormals/dbln": (
        "fc80fcb8e8c50d274d459ea1e3edd631687d83fdd622f18f192d4306ae861e04"
    ),
    "vector/precip_30ynormals/head": (
        "389189d1b520e376565f048fd0dec5e28f930ef5a8a894cfc15efcf2dd28387a"
    ),
    "vector/precip_30ynormals/hist": (
        "150a070b316cade6c93611e11a08cb1434e7bfc623b89e6be69f5383d41da01a"
    ),
    "vector/precip_30ynormals/sidx": (
        "f9cd35399e7bbaca4595c71e496f1e631c80ce727211e8f332e281c65c5463a1"
    ),
    "vector/precip_30ynormals/topo": (
        "8ecdc3f63d823e0d0ca8ef35f356eb021043698e7b2edef86c875fea44d8aa8d"
    ),
    "vector/usgsgages/cidx": (
        "cc524477427cb2d4158d432c5f8fa47f4bbe845b96711701bf584f5e3c5c4676"
    ),
    "vector/usgsgages/coor": (
        "cf546ab60d7787ec9a9dc9512f0a56432e3a5de3cad875fda4de5d9aadd11ee9"
    ),
    "vector/usgsgages/dbln": (
        "50e3c145e45b2e7ec112466d258fb8b27affc29b4e1c89855249368e5d6f6ba8"
    ),
    "vector/usgsgages/head": (
        "9d2375f6356cec2414459bce19e89fe4f00fbe9b0d31f50a00c9a2b45322a3de"
    ),
    "vector/usgsgages/hist": (
        "138aaa18aab79fc948b27fea26cdd98214df6f04944a81fff71587f6340f9e0c"
    ),
    "vector/usgsgages/sidx": (
        "0664e190721130f0bcb2032026912e796e97acd23476e50fda44202586d870b1"
    ),
    "vector/usgsgages/topo": (
        "eef6d34ac81bbf459e722dd46d19afb9e54d91ed43885afc9b41d432f8a48d17"
    ),
}


class MissingDataset(AssertionError):
    """The North Carolina dataset was not found

    An AssertionError, so that pytest reports the test as failed.
    """


def find_dataset() -> Path:
    """Return the folder of the North Carolina dataset

    The folder named by VARIABLE, which must then be a GRASS project: an
    empty or wrong value is a mistake, not a reason to look elsewhere. An
    unset or empty VARIABLE takes the first project of DEFAULT_NAMES below
    ~/grassdata.

    :raises MissingDataset: with VARIABLE and DOWNLOAD in the message
    """
    value = os.environ.get(VARIABLE)
    if value:
        path = Path(value).expanduser()
        if is_location_valid(path):
            return path
        msg = (
            f"{VARIABLE}={value} is no GRASS project: it has no "
            f"PERMANENT/DEFAULT_WIND. Download the North Carolina sample "
            f"dataset from {DOWNLOAD}, unpack it and name the folder "
            f"{PROJECT_NAME} in {VARIABLE}."
        )
        raise MissingDataset(msg)
    candidates = [Path.home() / "grassdata" / name for name in DEFAULT_NAMES]
    for path in candidates:
        if is_location_valid(path):
            return path
    tried = " nor ".join(str(path) for path in candidates)
    msg = (
        f"The North Carolina sample dataset is missing: {VARIABLE} is not set "
        f"and neither {tried} is a GRASS project. Download it from {DOWNLOAD}, "
        f"unpack it and name the folder {PROJECT_NAME} in {VARIABLE}."
    )
    raise MissingDataset(msg)


def project_in_dataset(dataset: Path, parent: Path, name: str = PROJECT_NAME) -> Path:
    """Make the project parent/name whose PERMANENT is a link to the dataset's

    Returns the path of the project, which has no mapset but PERMANENT. A new
    mapset in it is a folder below parent, and the maps of the dataset are
    found as in the dataset. Writing into PERMANENT writes into the dataset,
    which snapshot() shows.
    """
    project = Path(parent) / name
    project.mkdir(parents=True)
    target = (Path(dataset) / "PERMANENT").resolve()
    (project / "PERMANENT").symlink_to(target, target_is_directory=True)
    return project


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _files_below(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(path for path in folder.rglob("*") if path.is_file())


def _table_digests(database: Path, tables) -> dict[str, str]:
    """The sha256 of the schema and the rows of each table that exists

    The schema is every statement of the table in sqlite_master (the table
    and its indexes), the rows come in the order of their rowid; each as the
    repr of its tuple, one per line. The .dump of the sqlite3 shell would do
    as well, but the shell is not installed everywhere the tests run.
    """
    # mode=ro: reading must not create a journal or anything else next to
    # the database of the dataset.
    uri = f"{database.resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        digests = {}
        for table in tables:
            schema = connection.execute(
                "SELECT type, name, sql FROM sqlite_master "
                "WHERE tbl_name = ? ORDER BY type, name",
                (table,),
            ).fetchall()
            if not schema:
                continue
            rows = connection.execute(
                sql_statement("SELECT * FROM {table} ORDER BY rowid", table=table)
            ).fetchall()
            text = "\n".join(repr(row) for row in schema + rows)
            digests[f"table:{table}"] = hashlib.sha256(text.encode()).hexdigest()
        return digests
    finally:
        connection.close()


def fingerprint(dataset: Path) -> dict[str, str]:
    """Return the sha256 of every file and table of the data the examples use

    The keys are those of USED_DATA: the files of PROJECT_FILES, every file
    of the maps of RASTERS and VECTORS that exists (so an extra color table
    shows as a new key), and the table of each vector. A dataset with the
    recorded data gives a dict equal to USED_DATA.
    """
    permanent = Path(dataset) / "PERMANENT"
    files = [permanent / name for name in PROJECT_FILES]
    for name in RASTERS:
        files += [permanent / element / name for element in _RASTER_ELEMENTS]
        files += _files_below(permanent / "cell_misc" / name)
    for name in VECTORS:
        files += _files_below(permanent / "vector" / name)
    found = {
        path.relative_to(permanent).as_posix(): _file_digest(path)
        for path in files
        if path.is_file()
    }
    database = permanent / "sqlite" / "sqlite.db"
    if database.is_file():
        found.update(_table_digests(database, VECTORS))
    return found


def _size_and_time(path: Path, follow: bool = False) -> tuple[int, int]:
    status = path.stat() if follow else path.lstat()
    return status.st_size, status.st_mtime_ns


def snapshot(dataset: Path) -> dict[str, tuple[int, int]]:
    """Return size and modification time of everything in the dataset's PERMANENT

    The keys are the paths below PERMANENT, "." for PERMANENT itself;
    folders are included, because adding or removing an entry changes the
    time of its folder. Links are recorded, not followed.
    """
    permanent = Path(dataset) / "PERMANENT"
    entries = {".": _size_and_time(permanent, follow=True)}
    for root, folders, files in os.walk(permanent):
        for name in folders + files:
            path = Path(root, name)
            entries[path.relative_to(permanent).as_posix()] = _size_and_time(path)
    return entries


def differences(expected: dict, found: dict) -> list[str]:
    """Return "missing: key", "new: key" or "changed: key" for each key that
    differs, in the order of the keys"""
    lines = []
    for key in sorted(expected.keys() | found.keys()):
        if key not in found:
            lines.append(f"missing: {key}")
        elif key not in expected:
            lines.append(f"new: {key}")
        elif expected[key] != found[key]:
            lines.append(f"changed: {key}")
    return lines
