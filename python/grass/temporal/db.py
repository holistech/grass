"""Access to the temporal database: connections and SQL literals

SPDX-FileCopyrightText: 2011-2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

from __future__ import annotations

import contextlib
import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .core import SQLDatabaseInterfaceConnection


def sql_literal(value: object, dbmi_paramstyle: str = "qmark") -> str:
    """Write a Python value as a literal of an SQL statement

    This is the text that mogrify_sql_statement() puts in place of a
    placeholder when SQLite has to give a statement as text. Text is put in
    single quotes with the quotes inside doubled, as SQLite escapes them;
    None is NULL; a float that is not finite is NULL too, because SQLite has
    no literal for inf and nan and would read the bare word as a column name
    (statistics of a map with infinite values are unknown, which is what NULL
    says). Floats have six decimals and datetimes are written with
    str(), so microseconds stay. The SQLite adapter, which stores the values
    of a statement with arguments, drops them; which of the two is right is
    undecided, and the difference is kept as it was.

    :param value: The value
    :param dbmi_paramstyle: The parameter style of the backend; only "qmark"
                            (SQLite) is supported, because psycopg2 quotes
                            with the help of its connection (cursor.mogrify)
    :raises ValueError: for any other parameter style
    """
    if dbmi_paramstyle != "qmark":
        msg = (
            f"No SQL literal without a connection for parameter style {dbmi_paramstyle}"
        )
        raise ValueError(msg)
    if value is None:
        return "NULL"
    if isinstance(value, int):
        return "%d" % value
    if isinstance(value, float) and not math.isfinite(value):
        return "NULL"
    if isinstance(value, float):
        return "%f" % value
    # Default is a string, this works for datetime objects too
    return "'%s'" % str(value).replace("'", "''")


@contextlib.contextmanager
def connection(
    dbif: SQLDatabaseInterfaceConnection | None = None,
) -> Iterator[SQLDatabaseInterfaceConnection]:
    """Give a connected database interface and close it again if opened here

    Replaces the pair of init_dbif() and the test of connection_state_changed
    before every return. A connection that is passed in and already connected
    is handed on as it is and stays open. Without one, or with one that is not
    connected, a connection is made and closed when the block ends, also when
    it ends with an exception such as the FatalError of msgr.fatal().

    :param dbif: The database interface of the caller, or None
    """
    from .core import init_dbif  # noqa: PLC0415

    dbif, connection_state_changed = init_dbif(dbif)
    try:
        yield dbif
    finally:
        if connection_state_changed:
            dbif.close()
