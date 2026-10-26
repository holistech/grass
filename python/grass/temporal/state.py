"""The state of a temporal session and the initialisation of the framework

All what init() finds out about the session lives in one object, STATE: the
database backend, the mapset, the messenger and the C interface. The functions
get_*() of this module read it; nothing else writes to it.

SPDX-FileCopyrightText: 2011-2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:author: Soeren Gebbert
"""

from __future__ import annotations

import atexit
import multiprocessing.util  # noqa: F401
import os
from pathlib import Path

import grass.script as gs
from grass.pygrass import messages
from grass.script.utils import decode
from grass.tools import Tools

from .c_libraries_interface import CLibrariesInterface

tools = Tools()

# The version of the temporal framework
# this value must be an integer larger than 0
# Increase this value in case of backward incompatible changes in the TGIS API
tgis_version = 2
# The version of the temporal database since framework and database version
# can differ this value must be an integer larger than 0
# Increase this value in case of backward incompatible changes
# temporal database SQL layout
tgis_db_version = 3


class TgisState:
    """What init() found out about the session of the process

    :ivar backend: The database backend, "sqlite" or "pg"
    :ivar database: The database string of t.connect (never set by init())
    :ivar database_string: The database string with the GRASS variables
                           gisdbase, location and mapset substituted
    :ivar dbmi_paramstyle: The parameter style of the backend, "qmark" or
                           "pyformat"
    :ivar current_mapset: The mapset of the session, read once by init()
    :ivar current_location: The project of the session
    :ivar current_gisdbase: The database directory of the session
    :ivar enable_mapset_check: False after g.gisenv set=TGIS_DISABLE_MAPSET_CHECK=True.
                               Maps can then be registered in datasets of
                               other mapsets, which is highly experimental
    :ivar enable_timestamp_write: False after
                                  g.gisenv set=TGIS_DISABLE_TIMESTAMP_WRITE=True;
                                  C libraries can not read the timestamps of
                                  maps that were written with this switch off
    :ivar message_interface: The pygrass Messenger, a fast and exit safe
                             interface to the C message functions
    :ivar c_library_interface: The interface to libgis, libraster,
                               libraster3d and libvector
    :ivar raise_on_error: True to raise a FatalError exception in case of a
                          fatal error of the messenger, False to exit
    """

    def __init__(self) -> None:
        self.backend: str | None = None
        self.database: str | None = None
        self.database_string: str | None = None
        self.dbmi_paramstyle: str | None = None
        self.current_mapset: str | None = None
        self.current_location: str | None = None
        self.current_gisdbase: str | None = None
        self.enable_mapset_check = True
        self.enable_timestamp_write = True
        self.message_interface = None
        self.c_library_interface = None
        self.raise_on_error = False


STATE = TgisState()


def profile_function(func) -> None:
    """Profiling function provided by the temporal framework"""
    do_profiling = os.getenv("GRASS_TGIS_PROFILE")

    if do_profiling in {"True", "1"}:
        import cProfile  # noqa: PLC0415
        import io  # noqa: PLC0415
        import pstats  # noqa: PLC0415

        pr = cProfile.Profile()
        pr.enable()
        func()
        pr.disable()
        s = io.StringIO()
        sortby = "cumulative"
        ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        ps.print_stats()
        print(s.getvalue())
    else:
        func()


def get_tgis_backend() -> str | None:
    """Return the temporal GIS backend as string

    :returns: either "sqlite" or "pg"
    """
    return STATE.backend


def get_tgis_database() -> str | None:
    """Return the temporal database string specified with t.connect"""
    return STATE.database


def get_tgis_dbmi_paramstyle() -> str | None:
    """Return the temporal database backend parameter style

    :returns: "qmark" or ""
    """
    return STATE.dbmi_paramstyle


def get_current_mapset() -> str | None:
    """Return the current mapset

    This is the fastest way to receive the current mapset.
    The current mapset is set by init() and stored in the session state.
    """
    return STATE.current_mapset


def get_current_location() -> str | None:
    """Return the current location

    This is the fastest way to receive the current location.
    The current location is set by init() and stored in the session state.
    """
    return STATE.current_location


def get_current_gisdbase() -> str | None:
    """Return the current gis database (gisdbase)

    This is the fastest way to receive the current gisdbase.
    The current gisdbase is set by init() and stored in the session state.
    """
    return STATE.current_gisdbase


def get_enable_mapset_check():
    """Return True if the mapsets should be checked while insert, update,
    delete requests and space time dataset registration.

    If this switch is True, then maps can only be registered
    in space time datasets with the same mapset. In addition, only maps in
    the current mapset can be inserted, updated or deleted from the temporal
    database.
    Overwrite this switch by: g.gisenv set="TGIS_DISABLE_MAPSET_CHECK=True"

    .. warning::

        Be aware to face corrupted temporal database in case this
        switch is set to False. This feature is highly
        experimental and violates the grass permission guidance.

    """
    return STATE.enable_mapset_check


def get_enable_timestamp_write():
    """Return True if the map timestamps should be written to the spatial
    database metadata as well.

    If this switch is True, the timestamps of maps will be
    written as textfiles for each map that will be inserted or updated in
    the temporal database using the C-library timestamp interface.
    Overwrite this switch by: g.gisenv set="TGIS_DISABLE_TIMESTAMP_WRITE=True"

    .. warning::

        Be aware that C-libraries can not access timestamp information if
        they are not written as spatial database metadata, hence modules
        that make use of timestamps using the C-library interface will not
        work with maps that were created without writing the timestamps.
    """
    return STATE.enable_timestamp_write


def get_tgis_database_string() -> str | None:
    """Return the preprocessed temporal database string

    This string is the temporal database string set with t.connect
    that was processed to substitute location, gisdbase and mapset
    variables.
    """
    return STATE.database_string


def _init_tgis_message_interface(raise_on_error: bool = False) -> None:
    """Initiate the message interface

    :param raise_on_error: If True raise a FatalError exception in case of
                           a fatal error, call sys.exit(1) otherwise
    """
    if STATE.message_interface is None:
        STATE.message_interface = messages.get_msgr(raise_on_error=raise_on_error)
    msgr = STATE.message_interface
    # get_msgr() hands out one messenger per process, so the mode of an
    # earlier init() would stay.
    msgr.set_raise_on_error(raise_on_error)
    # The messenger of an earlier session was stopped by init(), but
    # get_msgr() returns it again. Restart its server here, before the C
    # interface starts its threads: a restart on first use would fork a
    # process with threads.
    if not msgr.server.is_alive():
        msgr.client_conn.close()
        msgr.server_conn.close()
        msgr.start_server()


def get_tgis_message_interface():
    """Return the temporal GIS message interface which is of type
    grass.pygrass.message.Messenger()

    Use this message interface to print messages to stderr using the
    GRASS C-library messaging system.
    """
    return STATE.message_interface


def _init_tgis_c_library_interface() -> None:
    """Start the interface to the C libraries if it is not running"""
    if STATE.c_library_interface is None:
        STATE.c_library_interface = CLibrariesInterface()


def get_tgis_c_library_interface():
    """Return the C-library interface that
    provides a fast and exit safe interface to the C-library libgis,
    libraster, libraster3d and libvector functions
    """
    return STATE.c_library_interface


def set_raise_on_error(raise_exp: bool = True):
    """Define behavior on fatal error, invoked using the tgis messenger
    interface (msgr.fatal())

    The messenger interface will be restarted using the new error policy

    :param raise_exp: True to raise a FatalError exception instead of calling
                      sys.exit(1) when using the tgis messenger interface

    .. code-block:: pycon

        >>> import grass.temporal as tgis
        >>> tgis.init()
        >>> ignore = tgis.state.set_raise_on_error(False)
        >>> msgr = tgis.get_tgis_message_interface()
        >>> tgis.state.get_raise_on_error()
        False
        >>> msgr.fatal("Ohh no no no!")
        Traceback (most recent call last):
          File "__init__.py", line 239, in fatal
            sys.exit(1)
        SystemExit: 1

        >>> tgis.state.set_raise_on_error(True)
        False
        >>> msgr.fatal("Ohh no no no!")
        Traceback (most recent call last):
            ...
        grass.exceptions.FatalError: Ohh no no no!

    :returns: current status
    """
    previous = STATE.raise_on_error
    STATE.raise_on_error = raise_exp

    if STATE.message_interface:
        STATE.message_interface.set_raise_on_error(raise_exp)
    else:
        _init_tgis_message_interface(raise_exp)

    return previous


def get_raise_on_error():
    """Return True if a FatalError exception is raised instead of calling
    sys.exit(1) in case a fatal error was invoked with msgr.fatal()
    """
    return STATE.raise_on_error


def get_tgis_version():
    """Get the supported version of the temporal framework

    :returns: The version number of the temporal framework as integer
    """
    return tgis_version


def get_tgis_db_version():
    """Get the supported version of the temporal database

    :returns: The version number of the temporal database as integer
    """
    return tgis_db_version


def stop_subprocesses() -> None:
    """Stop the messenger and C-interface subprocesses
    that are started by tgis.init()
    """
    if STATE.message_interface:
        STATE.message_interface.stop()
    if STATE.c_library_interface:
        STATE.c_library_interface.stop()


# Importing multiprocessing.util registers the multiprocessing exit handler,
# so this function, registered later, runs before it (atexit is LIFO) and stops
# the servers before multiprocessing terminates them.
atexit.register(stop_subprocesses)


def _read_session() -> dict:
    """Read the session and prepare the state for it

    The message and C-library subprocesses inherit GISRC at spawn time,
    so a session change leaves them bound to the old (possibly deleted)
    session. They are stopped here so that _start_servers() respawns them in
    the current environment.

    :return: The GRASS environment of the session
    """
    grassenv = gs.gisenv()

    new_mapset = grassenv["MAPSET"]
    new_location = grassenv["LOCATION_NAME"]
    new_gisdbase = grassenv["GISDBASE"]

    if STATE.current_mapset is not None and (
        STATE.current_mapset != new_mapset
        or STATE.current_location != new_location
        or STATE.current_gisdbase != new_gisdbase
    ):
        if STATE.message_interface is not None:
            STATE.message_interface.stop()
            STATE.message_interface = None
        if STATE.c_library_interface is not None:
            STATE.c_library_interface.stop()
            STATE.c_library_interface = None

    # Defaults for the TGIS DB, overwritten by _select_backend()
    STATE.backend = "sqlite"
    STATE.database_string = None
    STATE.dbmi_paramstyle = "qmark"

    # Kept in the state for faster access
    STATE.current_mapset = new_mapset
    STATE.current_location = new_location
    STATE.current_gisdbase = new_gisdbase
    return grassenv


def _apply_raise_policy() -> None:
    """Raise on error also if the environment or the script library say so"""
    if os.getenv("GRASS_TGIS_RAISE_ON_ERROR") in {"True", "1"}:
        STATE.raise_on_error = True

    # Check if the script library raises on error,
    # if so we do the same
    if gs.get_raise_on_error() is True:
        STATE.raise_on_error = True


def _start_servers() -> None:
    """Start the messenger and the C-library interface"""
    _init_tgis_message_interface(STATE.raise_on_error)
    _init_tgis_c_library_interface()
    STATE.message_interface.debug(
        1, ("Raise on error id: %s" % str(STATE.raise_on_error))
    )
    STATE.current_mapset = decode(gs.gisenv().get("MAPSET"))


def _apply_env_switches(grassenv: dict) -> None:
    """Read the two switches of the gisenv

    Both switches are read anew by every init(), so removing the variable
    from the gisenv switches the check back on.
    """
    msgr = STATE.message_interface
    STATE.enable_mapset_check = True
    if grassenv.get("TGIS_DISABLE_MAPSET_CHECK") in {"True", "1"}:
        STATE.enable_mapset_check = False
        msgr.warning("TGIS_DISABLE_MAPSET_CHECK is True")

    STATE.enable_timestamp_write = True
    if grassenv.get("TGIS_DISABLE_TIMESTAMP_WRITE") in {"True", "1"}:
        STATE.enable_timestamp_write = False
        msgr.warning("TGIS_DISABLE_TIMESTAMP_WRITE is True")


def _import_driver(name: str):
    """Return the Python module of a database driver (sqlite3 or psycopg2)"""
    msgr = STATE.message_interface
    if name == "sqlite3":
        try:
            import sqlite3  # noqa: PLC0415
        except ImportError:
            msgr.error(
                "Unable to locate the sqlite SQL Python interface module sqlite3."
            )
            raise
        return sqlite3
    try:
        import psycopg2  # noqa: PLC0415
    except ImportError:
        msgr.error(
            "Unable to locate the Postgresql SQL Python interface module psycopg2."
        )
        raise
    return psycopg2


def _select_backend() -> None:
    """Find the driver and the database string of the mapset with t.connect

    Sets the backend, the database string and the parameter style.
    """
    msgr = STATE.message_interface
    ciface = STATE.c_library_interface
    msgr.debug(1, "Initiate the temporal database")
    # We must run t.connect at first to create the temporal database and to
    # get the environmental variables
    gs.run_command("t.connect", flags="c", superquiet=True)

    driver_string = ciface.get_driver_name(STATE.current_mapset)
    database_string = ciface.get_database_name(STATE.current_mapset)

    if driver_string is not None and driver_string != "":
        driver_string = decode(driver_string)
        if driver_string == "sqlite":
            STATE.backend = driver_string
            dbmi = _import_driver("sqlite3")
        elif driver_string == "pg":
            STATE.backend = driver_string
            dbmi = _import_driver("psycopg2")
        else:
            msgr.fatal(
                _(
                    "Unable to initialize the temporal DBMI interface. "
                    "Please use t.connect to specify the driver and the"
                    " database string"
                )
            )
    else:
        # Set the default sqlite3 connection in case nothing was defined
        gs.run_command("t.connect", flags="d", superquiet=True)
        STATE.current_mapset = decode(gs.gisenv().get("MAPSET"))
        driver_string = ciface.get_driver_name(STATE.current_mapset)
        database_string = ciface.get_database_name(STATE.current_mapset)
        STATE.backend = driver_string
        dbmi = _import_driver("sqlite3")

    STATE.database_string = database_string
    STATE.dbmi_paramstyle = dbmi.paramstyle


def _database_exists(dbif) -> bool:
    """Return True if the temporal database has its tables already

    :param dbif: A database interface that is not connected
    """
    if STATE.backend == "sqlite":
        # Check path of the sqlite database
        if Path(STATE.database_string).exists():
            dbif.connect()
            # Check for raster_base table
            dbif.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name='raster_base';"
            )
            name = dbif.fetchone()
            dbif.close()
            return bool(name and name[0] == "raster_base")
    elif STATE.backend == "pg":
        # Connect to database
        dbif.connect()
        # Check for raster_base table
        dbif.execute(
            "SELECT EXISTS(SELECT * FROM information_schema.tables "
            "WHERE table_name=%s)",
            ("raster_base",),
        )
        exists = bool(dbif.fetchone()[0])
        dbif.close()
        return exists
    return False


def _check_versions(dbif) -> None:
    """Refuse a temporal database of a version this framework does not read

    :param dbif: A database interface that is not connected
    :raises FatalError: for another framework version or a database format
                        that is not supported (or exits, see raise_on_error)
    """
    from .schema import (  # noqa: PLC0415
        get_database_info_string,
        get_tgis_db_version_from_metadata,
        get_tgis_metadata,
    )

    msgr = STATE.message_interface
    if tgis_db_version > 2:
        backup_howto = _(
            "Run t.upgrade command to upgrade your temporal database.\n"
            "Consider creating a backup of your temporal database to avoid "
            "losing data in case something goes wrong.\n"
        )
    else:
        backup_howto = _(
            "You need to export it by "
            "restoring the GRASS version used for creating this DB."
            "Notes: Use t.rast.export and t.vect.export "
            "to make a backup of your"
            " existing space time datasets. To save the timestamps of"
            " your existing maps and space time datasets, use "
            "t.rast.list, t.vect.list and t.rast3d.list. "
            "You can register the existing time stamped maps easily if"
            " you export columns=id,start_time,end_time into text "
            "files and use t.register to register them again in new"
            " created space time datasets (t.create). After the backup"
            " remove the existing temporal database, a new one will be"
            " created automatically.\n"
        )

    dbif.connect()
    try:
        metadata = get_tgis_metadata(dbif)
    finally:
        dbif.close()

    # temporal framework version check
    for entry in metadata:
        if "tgis_version" in entry and entry[1] != str(get_tgis_version()):
            msgr.fatal(
                _(
                    "Unsupported temporal database: version mismatch."
                    "\n %(backup)s Supported temporal API version is:"
                    " %(api)i.\nPlease update your GRASS "
                    "installation.\nCurrent temporal database info:"
                    "%(info)s"
                )
                % (
                    {
                        "backup": backup_howto,
                        "api": get_tgis_version(),
                        "info": get_database_info_string(),
                    }
                )
            )

    # temporal database version check
    tgis_db_version_meta = get_tgis_db_version_from_metadata(metadata)
    if tgis_db_version_meta != tgis_db_version:
        message = _(
            "Temporal database version mismatch detected.\n{backup}"
            "Supported temporal database version is: {tdb}\n"
            "Your existing temporal database version: {ctdb}\n"
            "Current temporal database info: {info}"
        ).format(
            backup=backup_howto,
            tdb=tgis_db_version,
            ctdb=tgis_db_version_meta,
            info=get_database_info_string(),
        )

        if tgis_db_version_meta == 2 and tgis_db_version == 3:
            # version 3 is backward compatible with version 2
            msgr.warning(message)
        else:
            msgr.fatal(
                _(
                    "The format of your actual temporal database is "
                    "not supported any more. {m}"
                ).format(m=message)
            )


def _create_database() -> None:
    """Create the temporal database of the mapset

    The connection of the session may not contain the database of the current
    mapset, so a connection of its own is used.
    """
    from .db import DBConnection  # noqa: PLC0415
    from .schema import create_temporal_database  # noqa: PLC0415

    create_temporal_database(
        DBConnection(backend=STATE.backend, dbstring=STATE.database_string)
    )


def init(
    raise_fatal_error: bool = False,
    skip_db_version_check: bool = False,
    skip_db_init: bool = False,
):
    """Initialize the temporal GIS system.

    This function sets the session state and spawns the messenger and
    C-library interface subprocesses.

    Re-run this function in case the following GRASS variables change while
    the process runs:

    - MAPSET
    - LOCATION_NAME
    - GISDBASE
    - TGIS_DISABLE_MAPSET_CHECK
    - TGIS_DISABLE_TIMESTAMP_WRITE

    Re-run this function if the following t.connect variables change while
    the process runs:

    - temporal GIS driver (set by t.connect driver=)
    - temporal GIS database (set by t.connect database=)

    The following environmental variables are checked:

    - GRASS_TGIS_PROFILE (True, False, 1, 0)
    - GRASS_TGIS_RAISE_ON_ERROR (True, False, 1, 0)

    If not otherwise requested (skip_db_init), this function will check for
    the existence of a temporal database and its version in the current mapset.
    If the database does not exist, it will be created, using the database
    backend from GRASS environment variables, with the GRASS temporal database
    structure for raster, vector and raster3d maps as well as for the space-time
    dataset types strds, str3ds and stvds.

    .. warning::

        This functions must be called before any spatio-temporal processing
        can be started

    :param raise_fatal_error: Set this True to assure that the init()
                               function does not kill a persistent process
                               like the GUI. If set True a
                               grass.pygrass.messages.FatalError
                               exception will be raised in case a fatal
                               error occurs in the init process, otherwise
                               sys.exit(1) will be called.
    :param skip_db_version_check: Set this True to skip mismatch temporal
                                   database version check.
                                   Recommended to be used only for
                                   upgrade_temporal_database().
    :param skip_db_init: Set this True to allow init() to complete
                         without initializing, (version) checking or creating
                         a temporal database in the current mapset.
                         Use this when the calling process only needs the
                         global TGIS state (backend, mapset, interfaces)
                         but does not require a temporal database in the
                         current mapset for operations (like listing
                         datasets, getting metainformation, ...).
    """
    # db imports this module, so it can only be imported when init() runs
    from .db import SQLDatabaseInterfaceConnection  # noqa: PLC0415

    STATE.raise_on_error = raise_fatal_error
    grassenv = _read_session()
    _apply_raise_policy()
    _start_servers()
    _apply_env_switches(grassenv)

    if skip_db_init:
        return

    _select_backend()
    # One interface for both checks: each construction runs t.connect
    dbif = SQLDatabaseInterfaceConnection()
    if _database_exists(dbif):
        if not skip_db_version_check:
            _check_versions(dbif)
        return
    _create_database()
