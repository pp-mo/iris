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
Test of the verbose logging functionality for rules processing from
:mod:`iris.fileformats.rules`
"""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

# import iris tests first so that some things can be initialised before
# importing anything else
import iris.tests as tests

import os

import iris
import iris.fileformats.pp
import iris.config as config
import iris.fileformats.rules as rules


@tests.skip_data
class TestVerboseLogging(tests.IrisTest):
    def test_verbose_logging(self):
        # check that verbose logging no longer breaks in pp.save()
        # load some data, enable logging, and save a cube to PP.
        data_path = tests.get_data_path(('PP', 'simple_pp', 'global.pp'))
        cube = iris.load_cube(data_path)
        rules.log = rules._prepare_rule_logger(verbose=True,
                                               log_dir='/var/tmp')

        # Test writing to a file handle to test that the logger uses the
        # handle name
        with self.temp_filename(suffix='.pp') as mysavefile:
            iris.save(cube, mysavefile)

if __name__ == "__main__":
    tests.main()
