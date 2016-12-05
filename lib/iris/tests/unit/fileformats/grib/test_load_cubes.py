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
"""Unit tests for the `iris.fileformats.grib.load_cubes` function."""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

import iris.tests as tests

import iris
import iris.fileformats.grib
import iris.fileformats.grib.load_rules
import iris.fileformats.rules

from iris.fileformats.grib import load_cubes
from iris.tests import mock


class TestToggle(tests.IrisTest):
    def _test(self, mode, generator, converter):
        # Ensure that `load_cubes` defers to
        # `iris.fileformats.rules.load_cubes`, passing a correctly
        # configured `Loader` instance.
        with iris.FUTURE.context(strict_grib_load=mode):
            with mock.patch('iris.fileformats.rules.load_cubes') as rules_load:
                rules_load.return_value = mock.sentinel.RESULT
                result = load_cubes(mock.sentinel.FILES,
                                    mock.sentinel.CALLBACK,
                                    mock.sentinel.REGULARISE)
                if mode:
                    kw_args = {}
                else:
                    kw_args = {'auto_regularise': mock.sentinel.REGULARISE}
                loader = iris.fileformats.rules.Loader(
                    generator, kw_args,
                    converter, None)
                rules_load.assert_called_once_with(mock.sentinel.FILES,
                                                   mock.sentinel.CALLBACK,
                                                   loader)
                self.assertIs(result, mock.sentinel.RESULT)

    def test_sloppy_mode(self):
        # Ensure that `load_cubes` uses:
        #   iris.fileformats.grib.grib_generator
        #   iris.fileformats.grib.load_rules.convert
        self._test(False, iris.fileformats.grib.grib_generator,
                   iris.fileformats.grib.load_rules.convert)

    def test_strict_mode(self):
        # Ensure that `load_cubes` uses:
        #   iris.fileformats.grib.message.GribMessage.messages_from_filename
        #   iris.fileformats.grib._load_convert.convert
        self._test(
            True,
            iris.fileformats.grib.message.GribMessage.messages_from_filename,
            iris.fileformats.grib._load_convert.convert)


@tests.skip_data
class Test_load_cubes(tests.IrisTest):

    def test_reduced_raw(self):
        # Loading a GRIB message defined on a reduced grid without
        # interpolating to a regular grid.
        gribfile = tests.get_data_path(
            ("GRIB", "reduced", "reduced_gg.grib2"))
        grib_generator = load_cubes(gribfile, auto_regularise=False)
        self.assertCML(next(grib_generator))


if __name__ == "__main__":
    tests.main()
