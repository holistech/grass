"""Run mapcalc statements and other jobs in child processes, a batch at a time

Used by the extraction and the map calculation of space time datasets, which
start one r.mapcalc, r3.mapcalc or v.extract per map.

SPDX-FileCopyrightText: 2012-2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import grass.script as gs
from grass.exceptions import CalledModuleError

if TYPE_CHECKING:
    from collections.abc import Callable


def run_in_batches(
    ctx,
    runner: Callable,
    statements: list,
    nprocs: int,
    progress: Callable[[int, int], None] | None = None,
    succeeded: list[int] | None = None,
) -> bool:
    """Run the statements nprocs at a time, each in a process of its own

    A value of nprocs below 1 runs all statements at once, as the nprocs option
    of the tools always did.

    Each batch is joined before the next starts, and the last one before the
    function returns, so the caller can read every result.

    progress, if given, is called as progress(done, total) after each batch
    with the number of finished statements, so that it follows the
    computation and not the collecting of the statements.

    succeeded, if given, gets the index in statements of every process that
    ended without an error, also from the batch in which another one failed.
    The caller needs it to remove what a failed run made and to leave what it
    did not make.

    :param ctx: The multiprocessing context that makes the processes
    :param runner: The function a process runs, called with one statement
    :param statements: The arguments of the processes, one each
    :param nprocs: The number of processes that run at the same time
    :param progress: Called with the number of finished statements and the total
    :param succeeded: A list to append the indices of the successful ones to
    :return: False if a statement failed
    """
    size = nprocs if nprocs >= 1 else max(len(statements), 1)
    for first in range(0, len(statements), size):
        processes = [
            ctx.Process(target=runner, args=(statement,))
            for statement in statements[first : first + size]
        ]
        for process in processes:
            process.start()
        for process in processes:
            process.join()
        if succeeded is not None:
            succeeded.extend(
                first + offset
                for offset, process in enumerate(processes)
                if process.exitcode == 0
            )
        if any(process.exitcode for process in processes):
            return False
        if progress:
            progress(min(first + size, len(statements)), len(statements))
    return True


def run_mapcalc(module: str, expression: str, *, nprocs: int | None = 1) -> None:
    """Run r.mapcalc or r3.mapcalc in quiet mode, to be run in a child process

    The process ends with the exit code 1 if the module fails, which is what
    run_in_batches() looks at.

    :param module: "r.mapcalc" or "r3.mapcalc"
    :param expression: The expression with the name of the result map
    :param nprocs: The number of threads of the module, None to leave the
                   option out and let the module decide
    """
    options = {} if nprocs is None else {"nprocs": nprocs}
    try:
        gs.run_command(
            module,
            expression=expression,
            overwrite=gs.overwrite(),
            quiet=True,
            **options,
        )
    except CalledModuleError:
        sys.exit(1)
