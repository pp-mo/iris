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
"""Integration tests for pickling things."""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests

import six.moves.cPickle as pickle

if tests.GRIB_AVAILABLE:
    import gribapi
    from iris.fileformats.grib.message import GribMessage


@tests.skip_data
@tests.skip_grib
class TestGribMessage(tests.IrisTest):
    def test(self):
        # Check that a GribMessage pickles without errors.
        path = tests.get_data_path(('GRIB', 'fp_units', 'hours.grib2'))
        messages = GribMessage.messages_from_filename(path)
        message = next(messages)
        with self.temp_filename('.pkl') as filename:
            with open(filename, 'wb') as f:
                pickle.dump(message, f)

    def test_data(self):
        # Check that GribMessage.data pickles without errors.
        path = tests.get_data_path(('GRIB', 'fp_units', 'hours.grib2'))
        messages = GribMessage.messages_from_filename(path)
        message = next(messages)
        with self.temp_filename('.pkl') as filename:
            with open(filename, 'wb') as f:
                pickle.dump(message.data, f)


if __name__ == '__main__':
    tests.main()
