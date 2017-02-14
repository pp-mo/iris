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


# Whether to recognise biggus arrays as lazy, *as well as* dask.
# NOTE: in either case, this module will not *make* biggus arrays, only dask.
_SUPPORT_BIGGUS = True

# Whether to translate masked arrays to+from NaNs, when converting to+from lazy
# (dask) :  N.B. Dask currently has no support for masked arrays.
_TRANSLATE_MASKS = True

if _SUPPORT_BIGGUS:
    import biggus


def is_lazy_data(data):
    """
    Return whether the argument is an Iris 'lazy' data array.

    At present, this means simply a Dask array.
    We determine this by checking for a "compute" property.
    NOTE: ***for now only*** accept Biggus arrays also.

    """
    result = hasattr(data, 'compute')
    if not result and _SUPPORT_BIGGUS:
        result = isinstance(data, biggus.Array)
    return result


def as_concrete_data(data):
    """
    Return the actual content of the argument, as a numpy array.

    If lazy, return the realised data, otherwise return the argument unchanged.

    """
    if is_lazy_data(data):
        if _SUPPORT_BIGGUS and isinstance(data, biggus.Array):
            # Realise biggus array.
            # treat all as masked, for standard cube.data behaviour.
            data = data.masked_array()
        else:
            # Grab a fill value, in case this is just a converted masked array.
            fill_value = getattr(data, 'fill_value', None)
            # Realise dask array.
            data = data.compute()
            if _TRANSLATE_MASKS:
                # Convert NaN arrays into masked arrays for Iris' consumption.
                if isinstance(data.flat[0], np.float):
                    mask = np.isnan(data)
                    data = np.ma.masked_array(data, mask=mask,
                                              fill_value=fill_value)
    return data


# A magic value, borrowed from biggus
_MAX_CHUNK_SIZE = 8 * 1024 * 1024 * 2


def as_lazy_data(data):
    """
    Return a lazy equivalent of the argument, as a lazy array.

    For an existing lazy array, return it unchanged.
    Otherwise, return the argument wrapped with dask.array.from_array.
    This assumes the underlying object has numpy-array-like properties.

    .. Note::

        For now at least, chunksize is set to an arbitrary fixed value.

    """
    if not is_lazy_data(data):
        if isinstance(data, np.ma.MaskedArray):
            # record the original fill value.
            fill_value = data.fill_value
            if _TRANSLATE_MASKS:
                # Use with NaNs replacing the mask.
                data = array_masked_to_nans(data)
        else:
            fill_value = None
        data = da.from_array(data, chunks=_MAX_CHUNK_SIZE)
        # Attach any fill value to the dask object.
        # Note: this is not passed on to dask arrays derived from this one.
        data.fill_value = fill_value
    return data


def array_masked_to_nans(array):
    """
    Convert a masked array to a normal array with NaNs at masked points.

    This is used for dask integration, as dask does not support masked arrays.
    Note that any fill value will be lost.

    """
    if np.ma.is_masked(array):
        # Array has some masked points : use unmasked near-equivalent.
        if array.dtype.kind == 'f':
            # Floating : convert the masked points to NaNs.
            array = array.filled(np.nan)
        else:
            # Integer : no conversion (i.e. do *NOT* fill with fill value)
            # array = array.filled()
            array = array.data
    else:
        # Ensure result is not masked (converts arrays with empty masks).
        if isinstance(array, np.ma.MaskedArray):
            array = array.data
    return array


def array_nans_to_masked(array):
    """
    Convert an array into a masked array, masking any NaN points.

    """
    if (not isinstance(array, np.ma.masked_array) and
            array.dtype.kind == 'f'):
        mask = np.isnan(array)
        if np.any(mask):
            # Turn any unmasked array with NaNs into a masked array.
            array = np.ma.masked_array(array, mask=mask)
    return array
