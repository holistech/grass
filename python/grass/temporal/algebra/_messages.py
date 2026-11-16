"""Warnings of the algebra core

SPDX-FileCopyrightText: 2026 Soeren Gebbert
SPDX-FileCopyrightText: GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

import warnings

from grass.temporal.state import get_tgis_message_interface


def warn(message):
    """Warn through grass.temporal, or through Python before tgis.init()"""
    # The messenger of grass.temporal exists only after init(), but the
    # operations on series need no session.
    messenger = get_tgis_message_interface()
    if messenger is None:
        warnings.warn(message, stacklevel=3)
    else:
        messenger.warning(message)
