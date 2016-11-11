# (C) British Crown Copyright 2014 - 2016, Met Office
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
Code for fast loading of structured UM data.

This module defines which pp-field elements take part in structured loading,
and provides creation of :class:`FieldCollation` objects from lists of
:class:`iris.fileformats.pp.PPField`.

"""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

import itertools

from netCDF4 import netcdftime
import numpy as np

from iris.fileformats.um._optimal_array_structuring import \
    optimal_array_structure

from biggus import ArrayStack
from iris.fileformats.pp import PPField3


class FieldCollation(object):
    """
    An object representing a group of UM fields with array structure that can
    be vectorized into a single cube.

    For example:

    Suppose we have a set of 28 fields repeating over 7 vertical levels for
    each of 4 different data times.  If a FieldCollation is created to contain
    these, it can identify that this is a 4*7 regular array structure.

    This FieldCollation will then have the following properties:

    * within 'element_arrays_and_dims' :
        Element 'blev' have the array shape (7,) and dims of (1,).
        Elements 't1' and 't2' have shape (4,) and dims (0,).
        The other elements (lbft, lbrsvd4 and lbuser5) all have scalar array
        values and dims=None.

    .. note::

        If no array structure is found, the element values are all
        either scalar or full-length 1-D vectors.

    """
    def __init__(self, fields):
        """
        Args:

        * fields (iterable of :class:`iris.fileformats.pp.PPField`):
            The fields in the collation.

        """
        self._fields = tuple(fields)
        self._data_cache = None
        assert len(self.fields) > 0
        self._structure_calculated = False
        self._vector_dims_shape = None
        self._primary_dimension_elements = None
        self._element_arrays_and_dims = None

    @property
    def fields(self):
        return self._fields

    @property
    def data(self):
        if not self._structure_calculated:
            self._calculate_structure()
        if self._data_cache is None:
            data_arrays = [f._data for f in self.fields]
            self._data_cache = \
                ArrayStack.multidim_array_stack(data_arrays,
                                                self.vector_dims_shape)
        return self._data_cache

    @property
    def vector_dims_shape(self):
        """The shape of the array structure."""
        if not self._structure_calculated:
            self._calculate_structure()
        return self._vector_dims_shape

    @property
    def _UNUSED_primary_dimension_elements(self):
        """A set of names of the elements which are array dimensions."""
        if not self._structure_calculated:
            self._calculate_structure()
        return self._primary_dimension_elements

    @property
    def element_arrays_and_dims(self):
        """
        Value arrays for vector metadata elements.

        A dictionary mapping element_name: (value_array, dims).

        The arrays are reduced to their minimum dimensions.  A scalar array
        has an associated 'dims' of None (instead of an empty tuple).

        """
        if not self._structure_calculated:
            self._calculate_structure()
        return self._element_arrays_and_dims

    def _field_vector_element_arrays(self):
        """Define the field components used in the structure analysis."""
        # Define functions to make t1 and t2 values as date-time tuples.
        # These depend on header version (PPField2 has no seconds values).
        def t1_fn(fld):
            return (fld.lbyr, fld.lbmon, fld.lbdat, fld.lbhr, fld.lbmin,
                    getattr(fld, 'lbsec', 0))

        def t2_fn(fld):
            return (fld.lbyrd, fld.lbmond, fld.lbdatd, fld.lbhrd, fld.lbmind,
                    getattr(fld, 'lbsecd', 0))

        # Return a list of (name, array) for the vectorizable elements.
        component_arrays = [
            ('t1', np.array([t1_fn(fld) for fld in self.fields])),
            ('t2', np.array([t2_fn(fld) for fld in self.fields])),
            ('lbft', np.array([fld.lbft for fld in self.fields])),
            ('blev', np.array([fld.blev for fld in self.fields])),
            ('lblev', np.array([fld.lblev for fld in self.fields])),
            ('bhlev', np.array([fld.bhlev for fld in self.fields])),
            ('bhrlev', np.array([fld.bhrlev for fld in self.fields])),
            ('brsvd1', np.array([fld.brsvd[0] for fld in self.fields])),
            ('brsvd2', np.array([fld.brsvd[1] for fld in self.fields])),
            ('brlev', np.array([fld.brlev for fld in self.fields]))
        ]
        return component_arrays

    # Static factors for the _time_comparable_int routine (seconds per period).
    _TIME_ELEMENT_MULTIPLIERS = np.cumprod([1, 60, 60, 24, 31, 12])[::-1]

    def _time_comparable_int(self, yr, mon, dat, hr, min, sec):
        """
        Return a single unique number representing a date-time tuple.

        This calculation takes no account of the time field's real calendar,
        instead giving every month 31 days, which preserves the required
        time ordering.

        """
        elements = np.array((yr, mon, dat, hr, min, sec))
        return np.sum(elements * self._TIME_ELEMENT_MULTIPLIERS)

    def _calculate_structure(self):
        # Make value arrays for the vectorisable field elements.
        element_definitions = self._field_vector_element_arrays()

        # Identify the vertical elements and payload.
        blev_array = dict(element_definitions).get('blev')
        vertical_elements = ('lblev', 'bhlev', 'bhrlev',
                             'brsvd1', 'brsvd2', 'brlev')

        # Make an ordering copy.
        ordering_definitions = element_definitions[:]
        # Replace time value tuples with integers and bind the vertical
        # elements to the (expected) primary vertical element "blev".
        for index, (name, array) in enumerate(ordering_definitions):
            if name in ('t1', 't2'):
                array = np.array(
                    [self._time_comparable_int(*tuple(val)) for val in array])
                ordering_definitions[index] = (name, array)
            if name in vertical_elements and blev_array is not None:
                ordering_definitions[index] = (name, blev_array)

        # Perform the main analysis: get vector dimensions, elements, arrays.
        dims_shape, primary_elements, vector_element_arrays_and_dims = \
            optimal_array_structure(ordering_definitions,
                                    element_definitions)

        # Replace time tuples in the result with real datetime-like values.
        # N.B. so we *don't* do this on the whole (expanded) input arrays.
        for name in ('t1', 't2'):
            if name in vector_element_arrays_and_dims:
                arr, dims = vector_element_arrays_and_dims[name]
                arr_shape = arr.shape[:-1]
                extra_length = arr.shape[-1]
                # Flatten out the array apart from the last dimension,
                # convert to netcdftime objects, then reshape back.
                arr = np.array([netcdftime.datetime(*args)
                                for args in arr.reshape(-1, extra_length)]
                               ).reshape(arr_shape)
                vector_element_arrays_and_dims[name] = (arr, dims)

        # Write the private cache values, exposed as public properties.
        self._vector_dims_shape = dims_shape
        self._primary_dimension_elements = primary_elements
        self._element_arrays_and_dims = vector_element_arrays_and_dims

#        # Do a fast low-level equivalence check on all the header words we
#        # think should *not* vary within a phenomenon
#        _check_all_scalar_words_equal(self.fields)

        # Do all this only once.
        self._structure_calculated = True


# Whether we have initialised the PP indices global variables.
# A global flag provides a minimum-time-overhead test to initialise these
# only once, when they are first needed.
_PP_INDS_FETCHED = False


def _fetch_pp_inds():
    """Setup the PP indices global variables."""
    # We define global variables to encode fast access to specific PP header
    # words, because this method provides the fastest access.
    # Awkwardly, we must defer setting these up, to avoid circular imports.
    import iris.fileformats.pp as ifpp

    # Get a dictionary lookup version of pp-header
    # N.B. use version 3 -- version does not affect the ones we need.
    hdr = dict(ifpp.UM_HEADER_3)

    # Record the header indices of specific words for fast access by the
    # phenomenon collation function.
    global _PP_LBUSER4_INDEX, _PP_LBPROC_INDEX, _PP_LBUSER7_INDEX
    _PP_LBPROC_INDEX = hdr['lbproc'][0] - ifpp.UM_TO_PP_HEADER_OFFSET
    # LBUSER4 is the minor stash word
    _PP_LBUSER4_INDEX = hdr['lbuser'][3] - ifpp.UM_TO_PP_HEADER_OFFSET
    # LBUSER5 is a pseudo-level code
    _PP_LBUSER5_INDEX = hdr['lbuser'][4] - ifpp.UM_TO_PP_HEADER_OFFSET
    # LBUSER7 is the major stash word
    _PP_LBUSER7_INDEX = hdr['lbuser'][6] - ifpp.UM_TO_PP_HEADER_OFFSET

    # Define which header words we think "ought" to be the same throughout a
    # collated phenomenon.
    global _PP_STATIC_NAMES_AND_INDICES, _PP_STATIC_INDICES

    # Record the 'static' header words, as found in the PP header definition.
    _PP_STATIC_NAMES_AND_INDICES = [
#        # Likely problems
#        ('lbuser', 4),  # pseudo-level = LBUSER5
        # Less likely problems
        ('lbrsvd', 3),  # realisation = LBRSVD4
        ('lbfc', None),  # alternative phenom coding
        ('lbexp', None),  # experiment
        # Encoding types
        ('lbtim', None),  # time coding + period type
        ('lbcode', None),  # grid type
        ('lbvc', None), #vertical coordinate type
        ('lbhem', None),  # hemisphere
        ('lbproj', None),  # map projection
        ('bplat', None),  # rotated pole
        ('bplon', None),  # rotated pole
        ('bgor', None),  # rotated pole
        # Stable data aspects
        ('lbrow', None),  # field dims
        ('lbnpt', None),  # field dims
        # Unknown
        ('lbrvc', None),  # ??
        ('lbtyp', None),  # ??
        ]

    # Record the corresponding raw header indices, for fast access.
    _PP_STATIC_INDICES = [hdr[name][ind or 0] - ifpp.UM_TO_PP_HEADER_OFFSET
                          for name, ind in _PP_STATIC_NAMES_AND_INDICES]

    # Record that our deferred init is done.
    _PP_INDS_FETCHED = True


def _um_collation_key_function(field):
    """
    Standard collation key definition for fast structured field loading.

    The elements used here are the minimum sufficient to define the
    'phenomenon', as described for :meth:`group_structured_fields`.

    """
    return (field.lbuser[3], field.lbproc, field.lbuser[6])

#    # Use INT lbproc (should be faster)
#    result = (field.lbuser[3], int(field.lbproc), field.lbuser[6])

#    if not _PP_INDS_FETCHED:
#        # A global flag provides the minimum-time-overhead means of setting up
#        # the PP access indices only once, when we first need them.
#        _fetch_pp_inds()
#
#    # Use raw header access for speed.
#    result = (field._raw_header[_PP_LBUSER4_INDEX],  # minor stash word
#              field._raw_header[_PP_LBPROC_INDEX],  # statistics
#              field._raw_header[_PP_LBUSER7_INDEX],  # major stash word
##              field._raw_header[_PP_LBUSER5_INDEX],  # pseudo-level number
#              )

    return result


def _check_all_scalar_words_equal(fields):
    """
    Check that key header words are the same throughout a list of fields.

    The header words are accessed from the raw headers for speed.

    """
    # Which words to tested is defined by a global variable.
    # This has deferred initialisation, because it needs a deferred import.
    if not _PP_INDS_FETCHED:
        # A global flag provides the minimum-time-overhead means of setting up
        # the PP access indices only once, when we first need them.
        _fetch_pp_inds()

    # Uses raw header access for speed.
    mechanism_1 = True
    if mechanism_1:
        values = np.array([[field._raw_header[ind]
                            for ind in _PP_STATIC_INDICES]
                           for field in fields])
    else:
        # Alternative mechanism...
        values = np.array([field._raw_header for field in fields])
        values = values[:, _PP_STATIC_INDICES]

    all_same = np.all(values[1:] == values[0])
    if not all_same:
        msg = 'Phenomenon fields have different header elements:'
        for ind, (name, array_ind) in enumerate(_PP_STATIC_NAMES_AND_INDICES):
            name = (name if array_ind is None else
                    '{}{}'.format(name, array_ind+1))
            element_values_set = set(values[:, ind])
            if len(element_values_set) > 1:
                msg += '\n {} values : {}'.format(name, tuple(element_values_set))
        raise ValueError(msg)


def group_structured_fields(field_iterator):
    """
    Collect structured fields into identified groups whose fields can be
    combined to form a single cube.

    Args:

    * field_iterator (iterator of :class:`iris.fileformats.pp.PPField`):
        A source of PP or FF fields.  N.B. order is significant.

    The function sorts and collates on phenomenon-relevant metadata only,
    defined as the field components: 'lbuser[3]', 'lbuser[6]' and 'lbproc'.
    Each distinct combination of these defines a specific phenomenon (or
    statistical aggregation of one), and those fields appear as a single
    iteration result.

    Implicitly, within each result group, *all* other metadata components
    should be either:

    *  the same for all fields,
    *  completely irrelevant, or
    *  used by a vectorised rule function (such as
       :func:`iris.fileformats.pp_rules._convert_vector_time_coords`).

    Returns:
        A generator of FieldCollation objects, each of which contains a single
        collated group from the input fields.

    """
    _fields = sorted(field_iterator, key=_um_collation_key_function)
    for _, fields in itertools.groupby(_fields, _um_collation_key_function):
        yield FieldCollation(tuple(fields))
