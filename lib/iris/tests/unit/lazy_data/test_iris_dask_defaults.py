# (C) British Crown Copyright 2017, Met Office
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
Test :func:`iris._lazy data._iris_dask_defaults` function.

"""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests

import mock

import dask.context
from iris._lazy_data import _iris_dask_defaults


class Test__iris_dask_defaults(tests.IrisTest):
    def check_call_with_settings(self, test_settings_dict, expect_call=True):
        # Check the calls to 'dask.set_options' which result from calling
        # _iris_dask_defaults, with the given dask global settings.
        self.patch('dask.context._globals', test_settings_dict)
        set_options_patch = self.patch('dask.set_options')
        _iris_dask_defaults()
        self.assertEqual(dask.context._globals, test_settings_dict)
        if expect_call:
            expect_calls = [mock.call(get=dask.async.get_sync)]
        else:
            expect_calls = []
        self.assertEqual(set_options_patch.call_args_list, expect_calls)

    def test_no_user_options(self):
        self.check_call_with_settings({})

    def test_user_options__pool(self):
        self.check_call_with_settings({'pool': 5}, expect_call=False)

    def test_user_options__get(self):
        self.check_call_with_settings({'get': 'threaded'}, expect_call=False)

    def test_user_options__wibble(self):
        # Test a user-specified dask option that does not affect Iris.
        self.check_call_with_settings({'wibble': 'foo'})


if __name__ == '__main__':
    tests.main()
