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
Support for UM file types.

At present, only FieldsFiles and LBCs are supported.
Other types of UM file may fail to load correctly (or at all).

"""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa
import six

import os

import numpy as np

from mule.ff import FieldsFile, _DATA_DTYPES
from iris.fileformats._ff import DEFAULT_FF_WORD_DEPTH
from iris.fileformats.pp import make_pp_field

from iris._lazy_data import as_lazy_data

USE_OLD_IRIS_FF = False
_USE_IRIS_FF_VAR = os.environ.get('USE_OLD_IRIS_FF')
if _USE_IRIS_FF_VAR is not None:
    USE_OLD_IRIS_FF = bool(int(_USE_IRIS_FF_VAR))
#print('\n\n  env($USE_OLD_IRIS_FF)={!r}  :  USE_OLD_IRIS_FF={!r}\n\n'.format(
#     _USE_IRIS_FF_VAR, USE_OLD_IRIS_FF))

if USE_OLD_IRIS_FF:
    from iris.fileformats._ff import FF2PP
else:
    class MuleFieldDataProxy(object):
        def __init__(self, field, mule_file, filename):
            self.dtype = np.dtype(
                _DATA_DTYPES[mule_file.WORD_SIZE][field.lbuser1])
            self.shape = (mule_file.integer_constants.num_rows,
                          mule_file.integer_constants.num_cols)
            self.mule_file = mule_file
            self.filename = filename
            self._field_index = mule_file.fields.index(field)

        def __getitem__(self, keys):
            mule_file = self.mule_file
            original_file_still_open = \
                mule_file._source and not mule_file._source.closed
            if not original_file_still_open:
                # Temporarily open a new mule file + read a field from it.
                ff_file = open(self.filename)
                mule_file = FieldsFile.from_file(ff_file,
                                                 remove_empty_lookups=True)
            try:
                mule_field = mule_file.fields[self._field_index]
                data = mule_field.get_data()
                # Convert any MDIs to masked points, as in
                # pp._data_bytes_to_shaped_array.
                mdi = mule_field.bmdi
                if mdi in data:
                    if data.dtype.kind == 'i':
                        data = data.astype(np.dtype('f8'))
                    data[data == mdi] = np.nan
            finally:
                if not original_file_still_open:
                    # Close the temporary file.
                    ff_file.close()
            return data[keys]


    def FF2PP(filename, read_data=False,
              word_depth=DEFAULT_FF_WORD_DEPTH):
        """
        Get a stream of PPField objects from a FieldsFile.

        Now using Mule !

        """

        # Do not support alternate forms.
        assert read_data == False
        assert word_depth == 8

        with open(filename) as ff_file:
            mule_file = FieldsFile.from_file(ff_file,
                                             remove_empty_lookups=True)
            for mule_field in mule_file.fields:
                header = mule_field.raw[1:]
                pp_field = make_pp_field(header)
                # Attach data, action equivalent to pp._create_field_data.
                data_proxy = MuleFieldDataProxy(
                    mule_field, mule_file, filename)
                lazy_data = as_lazy_data(data_proxy, chunks=data_proxy.shape)
                pp_field.data = lazy_data
                correct_dtype = data_proxy.dtype.newbyteorder('=')
                if correct_dtype.kind in 'biu':
                    # Instruct DataManager to convert to original type.
                    pp_field.realised_dtype = correct_dtype
                yield pp_field


from iris.fileformats.pp import _load_cubes_variable_loader


def um_to_pp(filename, read_data=False, word_depth=None):
    """
    Extract the individual PPFields from within a UM file.

    Returns an iterator over the fields contained within the FieldsFile,
    returned as :class:`iris.fileformats.pp.PPField` instances.

    Args:

    * filename (string):
        Specify the name of the FieldsFile.

    Kwargs:

    * read_data (boolean):
        Specify whether to read the associated PPField data within
        the FieldsFile.  Default value is False.

    Returns:
        Iteration of :class:`iris.fileformats.pp.PPField`\s.

    For example::

        >>> for field in um.um_to_pp(filename):
        ...     print(field)

    """
    if word_depth is None:
        ff2pp = FF2PP(filename, read_data=read_data)
    else:
        ff2pp = FF2PP(filename, read_data=read_data,
                      word_depth=word_depth)

    # Note: unlike the original wrapped case, we will return an actual
    # iterator, rather than an object that can provide an iterator.
    return iter(ff2pp)


def load_cubes(filenames, callback, constraints=None,
               _loader_kwargs=None):
    """
    Loads cubes from a list of UM files filenames.

    Args:

    * filenames - list of filenames to load

    Kwargs:

    * callback - a function which can be passed on to
        :func:`iris.io.run_callback`

    .. note::

        The resultant cubes may not be in the order that they are in the
        file (order is not preserved when there is a field with
        orography references).

    """
    return _load_cubes_variable_loader(
        filenames, callback, FF2PP, constraints=constraints,
        loading_function_kwargs=_loader_kwargs)


def load_cubes_32bit_ieee(filenames, callback, constraints=None):
    """
    Loads cubes from a list of 32bit ieee converted UM files filenames.

    .. seealso::

        :func:`load_cubes` for keyword details

    """
    return load_cubes(filenames, callback, constraints=constraints,
                      _loader_kwargs={'word_depth': 4})
