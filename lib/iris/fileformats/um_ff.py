# (C) British Crown Copyright 2010 - 2015, Met Office
#
# This file is part of Iris.
#
# Iris is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Iris is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Iris.  If not, see <http://www.gnu.org/licenses/>.
"""
Provides UK Met Office Fields File (FF) format specific capabilities.

Support for :meth:`iris.load` via (what is now) :mod:`iris.experimental.um'.

At present, iris.load usage is switchable by :data:`iris.FUTURE.ff_load_um`.
    * When 'off', it uses :mod:`iris.fileformats._old_ff`, as previously.
    * When 'on' it uses this interface instead.

In future (if accepted), we can remove _old_ff, and the switch, but that is a
long way off.

"""

from __future__ import (absolute_import, division, print_function)

import iris
from iris.fileformats._old_ff import (
    load_cubes as oldff_load_cubes,
    load_cubes_32bit_ieee as oldff_load_cubes_32bit_ieee)


def load_cubes(filenames, callback, constraints=None):
    """
    Loads cubes from a list of fields files filenames.

    Args:

    * filenames - list of fields files filenames to load

    Kwargs:

    * callback - a function which can be passed on to
        :func:`iris.io.run_callback`

    .. note::

        The resultant cubes may not be in the order that they are in the
        file (order is not preserved when there is a field with
        orography references).

    """
    if iris.FUTURE.ff_load_um:
        msg = 'iris.load fieldsfile loading via experimental.um not provided'
        raise ValueError(msg)
    else:
        return oldff_load_cubes(filenames, callback, constraints)
#        pp._load_cubes_variable_loader(filenames, callback, FF2PP,
#                                       constraints=constraints)


def load_cubes_32bit_ieee(filenames, callback, constraints=None):
    """
    Loads cubes from a list of 32bit ieee converted fieldsfiles filenames.

    .. seealso::

        :func:`load_cubes` for keyword details

    """
    if iris.FUTURE.ff_load_um:
        msg = 'iris.load fieldsfile loading via experimental.um not provided'
        raise ValueError(msg)
    else:
        return oldff_load_cubes_32bit_ieee(filenames, callback, constraints)
#        return pp._load_cubes_variable_loader(filenames, callback, FF2PP,
#                                              {'word_depth': 4},
#                                              constraints=constraints)
