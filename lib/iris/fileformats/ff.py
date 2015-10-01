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

HACKED VERSION for proof-of-concept implementation via 'mule'.
"""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

import os
import warnings

import numpy as np
import numpy.ma as ma

import biggus
from iris.exceptions import NotYetImplementedError
from iris.fileformats._ff_cross_references import STASH_TRANS
from . import pp

import mule

#IMDI = -32768

#FF_HEADER_DEPTH = 256      # In words (64-bit).
DEFAULT_FF_WORD_DEPTH = 8  # In bytes.

# UM marker to signify empty lookup table entry.
_FF_LOOKUP_TABLE_TERMINATE = -99


#: Codes used in STASH_GRID which indicate the x coordinate is on the
#: edge of the cell.
X_COORD_U_GRID = (11, 18, 27)

#: Codes used in STASH_GRID which indicate the y coordinate is on the
#: edge of the cell.
Y_COORD_V_GRID = (11, 19, 28)

#: Grid codes found in the STASH master which are currently known to be
#: handled correctly. A warning is issued if a grid is found which is not
#: handled.
HANDLED_GRIDS = (1, 2, 3, 4, 5, 21, 26, 29) + X_COORD_U_GRID + Y_COORD_V_GRID


class Grid(object):
    """
    An abstract class representing the default/file-level grid
    definition for a FieldsFile.

    """
    def __init__(self, column_dependent_constants, row_dependent_constants,
                 real_constants, horiz_grid_type):
        """
        Create a Grid from the relevant sections of the FFHeader.

        Args:

        * column_dependent_constants (numpy.ndarray):
            The `column_dependent_constants` from a FFHeader.

        * row_dependent_constants (numpy.ndarray):
            The `row_dependent_constants` from a FFHeader.

        * real_constants (numpy.ndarray):
            The `real_constants` from a FFHeader.

        * horiz_grid_type (integer):
            `horiz_grid_type` from a FFHeader.

        """
        self.column_dependent_constants = column_dependent_constants
        self.row_dependent_constants = row_dependent_constants
        self.ew_spacing = real_constants.col_spacing
        self.ns_spacing = real_constants.row_spacing
        self.first_lat = real_constants.start_lat
        self.first_lon = real_constants.start_lon
        self.pole_lat = real_constants.north_pole_lat
        self.pole_lon = real_constants.north_pole_lon
        self.horiz_grid_type = horiz_grid_type

    def _x_vectors(self, subgrid):
        # Abstract method to return the X vector for the given sub-grid.
        raise NotImplementedError()

    def _y_vectors(self, subgrid):
        # Abstract method to return the X vector for the given sub-grid.
        raise NotImplementedError()

    def regular_x(self, subgrid):
        # Abstract method to return BZX, BDX for the given sub-grid.
        raise NotImplementedError()

    def regular_y(self, subgrid):
        # Abstract method to return BZY, BDY for the given sub-grid.
        raise NotImplementedError()

    def vectors(self, subgrid):
        """
        Return the X and Y coordinate vectors for the given sub-grid of
        this grid.

        Args:

        * subgrid (integer):
            A "grid type code" as described in UM documentation paper C4.

        Returns:
            A 2-tuple of X-vector, Y-vector.

        """
        x_p, x_u = self._x_vectors()
        y_p, y_v = self._y_vectors()
        x = x_p
        y = y_p
        if subgrid in X_COORD_U_GRID:
            x = x_u
        if subgrid in Y_COORD_V_GRID:
            y = y_v
        return x, y


class ArakawaC(Grid):
    """
    An abstract class representing an Arakawa C-grid.

    """
    def _x_vectors(self):
        x_p, x_u = None, None
        if self.column_dependent_constants is not None:
            x_p = self.column_dependent_constants[:, 0]
            if self.column_dependent_constants.shape[1] == 2:
                # Wrap around for global field
                if self.horiz_grid_type == 0:
                    x_u = self.column_dependent_constants[:-1, 1]
                else:
                    x_u = self.column_dependent_constants[:, 1]
        return x_p, x_u

    def regular_x(self, subgrid):
        """
        Return the "zeroth" value and step for the X coordinate on the
        given sub-grid of this grid.

        Args:

        * subgrid (integer):
            A "grid type code" as described in UM documentation paper C4.

        Returns:
            A 2-tuple of BZX, BDX.

        """
        bdx = self.ew_spacing
        bzx = self.first_lon - bdx
        if subgrid in X_COORD_U_GRID:
            bzx += 0.5 * bdx
        return bzx, bdx

    def regular_y(self, subgrid):
        """
        Return the "zeroth" value and step for the Y coordinate on the
        given sub-grid of this grid.

        Args:

        * subgrid (integer):
            A "grid type code" as described in UM documentation paper C4.

        Returns:
            A 2-tuple of BZY, BDY.

        """
        bdy = self.ns_spacing
        bzy = self.first_lat - bdy
        if subgrid in Y_COORD_V_GRID:
            bzy += self._v_offset * bdy
        return bzy, bdy


class NewDynamics(ArakawaC):
    """
    An Arakawa C-grid as used by UM New Dynamics.

    The theta and u points are at the poles.

    """

    _v_offset = 0.5

    def _y_vectors(self):
        y_p, y_v = None, None
        if self.row_dependent_constants is not None:
            y_p = self.row_dependent_constants[:, 0]
            if self.row_dependent_constants.shape[1] == 2:
                y_v = self.row_dependent_constants[:-1, 1]
        return y_p, y_v


class ENDGame(ArakawaC):
    """
    An Arakawa C-grid as used by UM ENDGame.

    The v points are at the poles.

    """

    _v_offset = -0.5

    def _y_vectors(self):
        y_p, y_v = None, None
        if self.row_dependent_constants is not None:
            y_p = self.row_dependent_constants[:-1, 0]
            if self.row_dependent_constants.shape[1] == 2:
                y_v = self.row_dependent_constants[:, 1]
        return y_p, y_v



_GRID_STAGGERING_CLASS = {3: NewDynamics, 6: ENDGame}

def _fieldsfile_grid(mule_file):
    """Return the Grid definition for the FieldsFile."""
    grid_staggering = mule_file.fixed_length_header.grid_staggering
    grid_class = _GRID_STAGGERING_CLASS.get(grid_staggering)
    if grid_class is None:
        grid_class = NewDynamics
        warnings.warn(
            'Staggered grid type: {} not currently interpreted, assuming '
            'standard C-grid'.format(grid_staggering))
    grid = grid_class(mule_file.column_dependent_constants,
                      mule_file.row_dependent_constants,
                      mule_file.real_constants,
                      mule_file.fixed_length_header.horiz_grid_type)
    return grid


def _mule_field_dtype(mule_field):
    # Get the type
#    dtype_template = _LBUSER_DTYPE_LOOKUP.get(
#        mule_field.lbuser1,
#        _LBUSER_DTYPE_LOOKUP['default'])
#    dtype_name = dtype_template.format(word_depth=DEFAULT_FF_WORD_DEPTH)
#    data_type = np.dtype(dtype_name)

    # NOTE for now, use the PP definitions, to make existing tests work.
    # NOTE the type assumptions for PP fields are DIFFERENT...
    # NOTE this probably means the answers are *wrong*
    # - we "ought" to have 8-byte data, but we dont
    # - as with existing ff code = also wrong?
    types_mapping = pp.LBUSER_DTYPE_LOOKUP
    data_type = types_mapping.get(mule_field.lbuser1, types_mapping['default'])
    return data_type


class _MuleFieldArraylikeWrapper(object):
    """
    Class to encode deferred access to the data payload of a fieldsfile field.

    Provides an array-like API, sufficient to wrap it in a biggus adaptor.
    Replaces the use of "pp.PPDataProxy" for field data in PP loading, when
    the PPfield is derived from a fieldsfile.

    The following properties are currently implemented:
        *   Biggus-wrappable deferred access.
        *   encode original field MDI value, and yield masked/unmasked data,
            as appropriate

    The following features are desirable, not yet implemented:
        *   LBC unpacking (not now)

    """
    def __init__(self, mule_field, data_type):
        self._mule_field = mule_field
        # Establish the minimum API necessary to wrap this as a Biggus array.
#        import pdb; pdb.set_trace()
        self.dtype = data_type
        self.fill_value = mule_field.bmdi  # ??is this right??
        self.shape = (mule_field.lbrow, mule_field.lbnpt)

    def __getitem__(self, keys):
        data = self._mule_field.get_data()[keys]
        if np.any(data == self.fill_value):
            data = ma.masked_values(data, self.fill_value, copy=False)
        return data


def _mule_field_data_accessor(mule_field, data_type):
    return biggus.NumpyArrayAdapter(_MuleFieldArraylikeWrapper(mule_field,
                                                               data_type))


class FF2PP(object):
    """A class to extract the individual PPFields from within a FieldsFile."""

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
        if word_depth != DEFAULT_FF_WORD_DEPTH:
            raise ValueError('non-64 bit fields files NOT YET SUPPORTED')

        self._filename = filename
        self._mule_file = mule.load_umfile(filename)
        self._ff_header = self._mule_file.fixed_length_header
#        self._ff_header = FFHeader(filename, word_depth=word_depth)
        self._word_depth = word_depth
        self._read_data = read_data
        if self._read_data:
            raise ValueError('read_data=True NOT YET SUPPORTED')

    def _extract_field(self):
        # FF table pointer initialisation based on FF LOOKUP table
        # configuration.

        table_index = self._ff_header.lookup_start
        table_entry_depth = self._ff_header.lookup_dim1
        table_entry_depth = table_entry_depth * self._word_depth  # in bytes
        if 1:

            is_boundary_packed = self._ff_header.dataset_type == 5
            if is_boundary_packed:
                raise ValueError('LBC variants NOT YET SUPPORTED')

            grid = _fieldsfile_grid(self._mule_file)

            for mule_field in self._mule_file.fields:
                header_longs = mule_field._lookup_ints
                if header_longs[0] == _FF_LOOKUP_TABLE_TERMINATE:
                    # There are no more FF LOOKUP table entries to read.
                    break
                header_floats = mule_field._lookup_reals
                header = tuple(header_longs) + tuple(header_floats)

                # Construct a PPField object and populate using the header_data
                # read from the current FF LOOKUP table.
                # (The PPField sub-class will depend on the header release
                # number.)
                field = pp.make_pp_field(header)

                # Fast stash look-up.
                stash_s = field.lbuser[3] // 1000
                stash_i = field.lbuser[3] % 1000
                stash = 'm{:02}s{:02}i{:03}'.format(field.lbuser[6],
                                                    stash_s, stash_i)
                stash_entry = STASH_TRANS.get(stash, None)
                if stash_entry is None:
                    subgrid = None
                    warnings.warn('The STASH code {0} was not found in the '
                                  'STASH to grid type mapping. Picking the P '
                                  'position as the cell type'.format(stash))
                else:
                    subgrid = stash_entry.grid_code
                    if subgrid not in HANDLED_GRIDS:
                        warnings.warn('The stash code {} is on a grid {} '
                                      'which has not been explicitly handled '
                                      'by the fieldsfile loader. Assuming the '
                                      'data is on a P grid.'.format(stash,
                                                                    subgrid))

                field.x, field.y = grid.vectors(subgrid)

                # Use the per-file grid if no per-field metadata is available.
                no_x = field.bzx in (0, field.bmdi) and field.x is None
                no_y = field.bzy in (0, field.bmdi) and field.y is None
                if no_x and no_y:
                    field.bzx, field.bdx = grid.regular_x(subgrid)
                    field.bzy, field.bdy = grid.regular_y(subgrid)
                    field.bplat = grid.pole_lat
                    field.bplon = grid.pole_lon
                elif no_x or no_y:
                    warnings.warn(
                        'Partially missing X or Y coordinate values.')

                # Check for LBC fields.
                is_boundary_packed = self._ff_header.dataset_type == 5
                if is_boundary_packed:
                    # Apply adjustments specific to LBC data.
                    self._adjust_field_for_lbc(field)

                # Determine PP field payload depth and type.
                data_type = _mule_field_dtype(mule_field)

                # Produce (yield) output fields.
                if is_boundary_packed:
                    fields = self._fields_over_all_levels(field)
                else:
                    fields = [field]
                for result_field in fields:
                    # Add a field data element.
                    if self._read_data:
                        raise ValueError('read_data=True NOT YET SUPPORTED')
                    else:
                        # Provide a biggus array as the data.
                        # This wraps the mule field data access (and so
                        # includes the unpacking support).
                        result_field._data = _mule_field_data_accessor(
                            mule_field, data_type)

                    yield result_field

    def ppfields_generator(self):
        """Return a generator of our fields, as _interpreted_ PPFields."""
        return pp._interpret_fields(self._extract_field())


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
    def fieldsfile_fields_generator(filepath, **kwargs):
        ff2pp = FF2PP(filepath, **kwargs)
        return ff2pp.ppfields_generator()

    return pp._load_cubes_variable_loader(filenames, callback,
                                          fieldsfile_fields_generator,
                                          constraints=constraints)

