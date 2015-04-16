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
        msg = ('iris.load of fieldsfiles via iris.experimental.um '
               'not provided for 32-bit files')
        raise ValueError(msg)


class DeferredArray(object):
    """
    A wrapper for array data, with deferred access to the actual values.

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

        This approach is known to be over-simplistic : We can't represent
        landmask-compressed data like this, because its shape is not known
        until we've found a corresponding landmask field.
        If we need to support landmask-compressed data, we must *either* change
        this approach, or resolve the shape of the data here+now by reference
        to the landmask in the same file.

    """
    fld = um_field
    shape = (fld.lbrow, fld.lbnpt)
    dtype = pp.LBUSER_DTYPE_LOOKUP.get(
        fld.lbuser1, pp.LBUSER_DTYPE_LOOKUP['default'])
    return biggus.NumpyArrayAdapter(
        DeferredArray(shape=shape, dtype=dtype,
                      deferred_fetch_call=lambda: fld.get_data()))


# Find the header indices of those header elements which get obscured by
# PPField property functions.
# Pre-calculate these, as it involves scanning the whole header description.
_SPLIT_INT_PROPERTY_NAMES = ('lbtim', 'lbcode', 'lbpack', 'lbproc')
_HEADER_SPLIT_INTS_INDICES = {}
for name, indices in pp.UM_HEADER_3:
    if name in _SPLIT_INT_PROPERTY_NAMES:
        # NOTE: none of these ones have multiple indices: just take the first.
        # NOTE: values are fortran indices, so subtract one here.
        _HEADER_SPLIT_INTS_INDICES[name] = indices[0] - 1


def fakeup_ppfield_bits(fld):
    """
    Adjust the properties of a field wrapper so that it can emulate a
    pp.PPField in pp_rules processing.

    fld is a :class:`_PPFieldWrapper` subtype which inherits from a um.Field.
    Most of the necessary header values to emulate a PPField are already
    present from um.Field, but some need 'fixing up'.

    """
    # Make array-type versions of lbuser, brsvd and lbrsvd.
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

    # Fix the PPField 'split integer' properties, which replace certain header
    # words with computed objects.  These won't work otherwise, as they depend
    # on the special __setattr__ implementation used in pp.PPField.
    for name, index in _HEADER_SPLIT_INTS_INDICES.iteritems():
        # Fetch the raw value - from the um header, as the um named property is
        # hidden by the PPField property function.
        raw_value = fld.int_headers[index]
        # Call the PPField setter function to enable normal PPField usage.
        # This replaces 'x' with a computed object (and stores a raw value
        # somewhere else, but not in the same way for all of them).
        setattr(fld, name, raw_value)


class _PPFieldWrapper(pp.PPFieldExtraPropertiesMixin):
    """
    A thin wrapper providing a mashup of um.Field and the 'extra' properties
    used by pp.PPField.

    The 'special' properties of PPField are added by the multiple imports.
    This class is effectively abstract, i.e. only used by inheriting it.

    """
    def __init__(self, um_field):
        """Construct a um.Field version of the provided field."""
        # Call the um constructor to add all the named access methods.
        super(type(um_field), self).__init__(
            int_headers=um_field.int_headers,
            real_headers=um_field.real_headers,
            data_provider=um_field._data_provider)
        # Adjust our properties to emulate a PPField for rules processing.
        fakeup_ppfield_bits(self)
        # Add a deferred acccess wrapper for the data.
        self._data = deferred_field_data(um_field)


class PPField2Wrapper(_PPFieldWrapper, pp.PPField2Mixin, um.Field2):
    """
    A PPField wrapper for a version-2 header.

    To the generic PPField 'extra' properties, this adds the PPField2-specific
    ones, and also inherits from um.Field2.

    """
    pass


class PPField3Wrapper(_PPFieldWrapper, pp.PPField3Mixin, um.Field3):
    """
    A PPField wrapper for a version-3 header.

    To the generic PPField 'extra' properties, this adds the PPField3-specific
    ones, and also inherits from um.Field3.

    """
    pass


def wrap_field_as_pplike(um_field):
    """Make a :class:`_PPFieldWrapper` wrapper from a :class:`um.Field`."""
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
    A convertor to extract the fields from a FieldsFile.

    Behaves as an iterator producing PPField-like objects.
    Uses :mod:`iris.experimental.um` for the FieldsFile access.

   """

    def __init__(self, filename, read_data=False,
                 word_depth=DEFAULT_FF_WORD_DEPTH):
        """
        An object that acts as a generator of fields contained within the
        FieldsFile.

        Args:

        * filename (string):
            Specify the name of the FieldsFile.

        Kwargs:

        * read_data (boolean):
            Specify whether to read the associated PPField data within
            the FieldsFile.  Default value is False.

        Returns:
            PPField generator.

        """
        self._filename = filename
        self._word_depth = word_depth
#        self._read_data = read_data
        if read_data:
            msg = ('iris.load of fieldsfiles via iris.experimental.um '
                   'does not support read_data=True.')
            raise(msg)

    def __iter__(self):
        # The key functionality : produce a stream of PPField-like results.
        return pp._interpret_fields(self._iter_fields())
        # NOTE: the stated purpose of post-filtering with pp._interpret_fields
        # is to "Turn the fields ... into useable fields".  It's needed because
        # the content of some fields isn't known without reference to other
        # fields -- the key instance being landmask-compressed data.
        # For simplicity, we are currently not supporting that.
        # See note above in 'deferred_field_data'.

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
