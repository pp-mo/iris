# (C) British Crown Copyright 2014 - 2015, Met Office
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
"""Integration tests for loading LBC fieldsfiles."""

from __future__ import (absolute_import, division, print_function)

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests

import iris


class TestSwitching(tests.IrisTest):
    def _check_load(self):
        filepath = tests.get_data_path(('FF', 'structured', 'small'))
        result = iris.load(filepath)
        return result

    def test_switch_default(self):
        result = self._check_load()
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], iris.cube.Cube)

    def test_switch_old(self):
        with iris.FUTURE.context(ff_load_um=False):
            result = self._check_load()
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], iris.cube.Cube)

    def test_switch_new(self):
        with iris.FUTURE.context(ff_load_um=True):
            msg = 'loading via experimental.um not provided'
            with self.assertRaisesRegexp(ValueError, msg):
                result = self._check_load()


if __name__ == "__main__":
    tests.main()
