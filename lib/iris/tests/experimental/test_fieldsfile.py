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
Test the fast loading of structured Fieldsfiles.

"""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

# import iris tests first so that some things can be initialised before
# importing anything else
import iris.tests as tests

from iris.experimental.fieldsfile import load


@tests.skip_data
class TestStructuredLoadFF(tests.IrisTest):
    def setUp(self):
        self.fname = tests.get_data_path(('FF', 'structured', 'small'))

    def test_simple(self):
        cube, = load(self.fname)
        self.assertCML(cube)

    def test_simple_callback(self):
        def callback(cube, field, filename):
            cube.attributes['processing'] = 'fast-ff'
        cube, = load(self.fname, callback=callback)
        self.assertCML(cube)


@tests.skip_data
class TestStructuredLoadPP(tests.IrisTest):
    def setUp(self):
        self.fname = tests.get_data_path(('PP', 'structured', 'small.pp'))

    def test_simple(self):
        [cube] = load(self.fname)
        self.assertCML(cube)

    def test_simple_callback(self):
        def callback(cube, field, filename):
            cube.attributes['processing'] = 'fast-pp'
        [cube] = load(self.fname, callback=callback)
        self.assertCML(cube)


if __name__ == "__main__":
    tests.main()
