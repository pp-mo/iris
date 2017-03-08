# (C) British Crown Copyright 2017, Met Office
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
Routines for lazy data handling.

To avoid replicating implementation-dependent test and conversion code.

"""
from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

import dask.array as da
import numpy as np


def is_lazy_data(data):
    """
    Return whether the argument is an Iris 'lazy' data array.

    At present, this means simply a Dask array.
    We determine this by checking for a "compute" property.
    NOTE: ***for now only*** accept Biggus arrays also.

    """
    result = hasattr(data, 'compute')
    return result


def as_concrete_data(data, filled=None, result_dtype=None):
    """
    Return the actual content of a lazy array, as a numpy array.

    If the data is a NumPy array, return it unchanged.

    If the data is lazy, return the realised result.

    Where lazy data contains NaNs these are translated by either filling or
    conversion to a masked array :

    *   if the "filled" keyword is given, any NaNs in the data are filled with
        this value.  The result is always a 'normal' numpy array.

    *   if the "filled" keyword is *not* given, then the result is a 'normal'
        NumPy array only if the data contains no NaNs :  If there *are* NaNs,
        we return instead return a *masked* array, masked at the NaN points.

    .. note::

        Any masked array returned has the default fill-value.

    """
    if is_lazy_data(data):
        # Realise dask array.
        data = data.compute()
        # Convert any missing data as requested.
        data = _array_nans_to_filled_or_masked(data, filled=filled,
                                               result_dtype=result_dtype)

    return data


def _array_nans_to_filled_or_masked(array, filled=None, result_dtype=None):
    # Convert any NaNs into a masked or filled array result.
    mask = np.isnan(array)
    if not np.all(~mask):
        # Some points have NaNs.
        if filled is not None:
            # Convert NaN arrays into filled data, for file storage.
            array[mask] = filled
        else:
            # Convert NaN arrays into masked arrays for Iris' consumption.
            array = np.ma.masked_array(array, mask=mask)

    if result_dtype is not None and array.dtype != result_dtype:
        # Force the required dtype.  This is used where masked integers may
        # occur : they are represented as floating NaN arrays.
        array = array.astype(result_dtype)

    return array


def array_masked_to_nans(array, mask=None):
    """
    Convert a masked array to a normal array with NaNs at masked points.
    This is used for dask integration, as dask does not support masked arrays.
    Note that any fill value will be lost.
    """
    if mask is None:
        mask = array.mask
    if array.dtype.kind == 'i':
        array = array.astype(np.dtype('f8'))
    array[mask] = np.nan
    return array
