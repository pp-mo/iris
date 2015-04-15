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

import biggus
import iris
import iris.experimental.um as um
from iris.fileformats._old_ff import (
    load_cubes as oldff_load_cubes,
    load_cubes_32bit_ieee as oldff_load_cubes_32bit_ieee,
    DEFAULT_FF_WORD_DEPTH)
from . import pp as pp


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
    if not iris.FUTURE.ff_load_um:
        return oldff_load_cubes(filenames, callback, constraints)

    result = pp._load_cubes_variable_loader(filenames, callback,
                                            PPlikeUmFieldsSource,
                                            constraints=constraints)
    return result


def load_cubes_32bit_ieee(filenames, callback, constraints=None):
    """
    Loads cubes from a list of 32bit ieee converted fieldsfiles filenames.

    .. seealso::

        :func:`load_cubes` for keyword details

    """
    if not iris.FUTURE.ff_load_um:
        return oldff_load_cubes_32bit_ieee(filenames, callback, constraints)
    else:
        msg = ('iris.load fieldsfile loading via experimental.um '
               'not provided for 32-bit files')
        raise ValueError(msg)
#        return pp._load_cubes_variable_loader(filenames, callback, FF2PP,
#                                              {'word_depth': 4},
#                                              constraints=constraints)


class DeferredArray(object):
    """
    A wrapper for a deferred array object.

    Shape + dtype are known, but fetch is only triggered by indexing.
    This is just enough to allow wrapping with a biggus.NumpyArrayAdapter.

    """
    def __init__(self, shape, dtype, deferred_fetch_call):
        self._shape = shape
        self._dtype = dtype
        self._fetch_call = deferred_fetch_call

    @property
    def shape(self):
        return self._shape

    @property
    def dtype(self):
        return self._dtype

    def __getitem__(self, keys):
        return self._fetch_call()[keys]


def deferred_field_data(um_field):
    """
    Wrap the data of a um.Field as a biggus.Array, with deferred loading.

    This object does not support writing to the array, but is functional for
    the usual deferred load purposes.

    .. note::

        Unfortunately, this approach is over-simplistic as we can't represent
        landmask-compressed data like this, because that does not have a known
        shape until it is linked to the landmask.
        URRRGH.

    """
    fld = um_field
    shape = (fld.lbrow, fld.lbnpt)
    dtype = pp.LBUSER_DTYPE_LOOKUP.get(
        fld.lbuser1, pp.LBUSER_DTYPE_LOOKUP['default'])
    return biggus.NumpyArrayAdapter(
        DeferredArray(shape=shape, dtype=dtype,
                      deferred_fetch_call=lambda : fld.get_data()))


def fake_ppfield_bits(um_field):
    fld = um_field
    fld.lbuser = [fld.lbuser1,
                  fld.lbuser2,
                  fld.lbuser3,
                  fld.lbuser4,
                  fld.lbuser5,
                  fld.lbuser6,
                  fld.lbuser7
                  ]
    fld.brsvd = [fld.brsvd1, fld.brsvd2, fld.brsvd3, fld.brsvd4]
    fld.lbrsvd = [fld.lbrsvd1, fld.lbrsvd2, fld.lbrsvd3, fld.lbrsvd4]
    lbtim = fld.int_headers[12]
    lbcode = fld.int_headers[15]
    lbpack = fld.int_headers[20]
    lbproc = fld.int_headers[24]
    fld.lbtim = lbtim
    fld.lbcode = lbcode
    fld.lbpack = lbpack
    fld.lbproc = lbproc


class PPField2Wrapper(pp.PPFieldExtraPropertiesMixin, pp.PPField2Mixin,
                      um.Field2):
    """
    A thin wrapper providing a mashup of um.Field and a pp.PPField.

    All 'special' methods of PPField2 are added by the multiple imports.

    """
    pass


class PPField3Wrapper(pp.PPFieldExtraPropertiesMixin, pp.PPField3Mixin,
                      um.Field3):
    """
    A thin wrapper providing a mashup of um.Field and a pp.PPField.

    All 'special' methods of PPField3 are added by the multiple imports.

    """
    def __init__(self, um_field):
        """Construct a um.Field version of the provided field."""
        super(um.Field3, self).__init__(
            int_headers=um_field.int_headers,
            real_headers=um_field.real_headers,
            data_provider=um_field._data_provider)
        self._data = deferred_field_data(um_field)
        fake_ppfield_bits(self)


def wrap_field_as_pplike(um_field):
    lbrel = um_field.lbrel
    if lbrel == 2:
        result = PPField2Wrapper(um_field)
    elif lbrel == 3:
        result = PPField3Wrapper(um_field)
    else:
        msg = 'unrecognised LBREL={}'
        raise ValueError(msg.format(lbrel))
    return result


class PPlikeUmFieldsSource(object):
    """
    A convertor producing PPFields from a FieldsFile.

    Behaves as an iterator producing PPField-like objects.
    Uses :mod:`iris.experimental.um` for the FieldsFile access.

   """

    def __init__(self, filename, read_data=False,
                 word_depth=DEFAULT_FF_WORD_DEPTH):
        """
        Create a FieldsFile to Post Process instance that returns a generator
        of PPFields contained within the FieldsFile.

        Args:

        * filename (string):
            Specify the name of the FieldsFile.

        Kwargs:

        * read_data (boolean):
            Specify whether to read the associated PPField data within
            the FieldsFile.  Default value is False.

        Returns:
            PPField generator.

        For example::

            >>> for field in ff.FF2PP(filename):
            ...     print(field)

        """
        self._filename = filename
        self._word_depth = word_depth
        self._read_data = read_data

    def __iter__(self):
        # The key functionality : produce a stream of PPField-like results.
        return pp._interpret_fields(self._iter_fields())

    def _iter_fields(self):
        # Return a stream of fields, 'wrapped' as PPField-compatible objects.
        open_file = um.FieldsFileVariant(self._filename)
        try:
            is_boundary_packed = \
                open_file.fixed_length_header.dataset_type == 5
            if is_boundary_packed:
                msg = 'FieldsFile is boundary-packed, which is not supported'
                raise ValueError(msg)

            for um_field in open_file.fields:
                # Skip 'blank' lookups.
                if um_field.int_headers[0] != -99:
                    # Wrap each um field to look like a PPField.
                    yield wrap_field_as_pplike(um_field)

        finally:
            open_file.close()

