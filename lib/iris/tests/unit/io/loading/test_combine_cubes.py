# Copyright Iris contributors
#
# This file is part of Iris and is released under the BSD license.
# See LICENSE in the root of the repository for full licensing details.
"""Unit tests for the :func:`iris.io.loading.combine_cubes` function.

Note: These tests are fairly extensive to cover functional uses within the loading
operations.
TODO: when function is public API, extend testing to the extended API options,
i.e. different types + defaulting of the 'options' arg, and **kwargs support.
"""

from unittest import mock

import pytest

from iris import LOAD_POLICY, LoadPolicy
from iris.io.loading import combine_cubes
from iris.tests.unit.io.loading.test_load_functions import cu


@pytest.fixture(params=list(LoadPolicy.SETTINGS.keys()))
def options(request):
    # N.B. "request" is a standard PyTest fixture
    return request.param  # Return the name of the attribute to test.


class Test_function:
    def test_mergeable(self, options):
        c1, c2 = cu(t=1), cu(t=2)
        c12 = cu(t=(1, 2))
        input_cubes = [c1, c2]
        result = combine_cubes(input_cubes, options)
        expected = [c12]  # same in all cases
        assert result == expected

    def test_catable(self, options):
        c1, c2 = cu(t=(1, 2)), cu(t=(3, 4))
        c12 = cu(t=(1, 2, 3, 4))
        input_cubes = [c1, c2]
        result = combine_cubes(input_cubes, options)
        expected = {
            "legacy": [c1, c2],  # standard options can't do this ..
            "default": [c1, c2],
            "recommended": [c12],  # .. but it works if you enable concatenate
            "comprehensive": [c12],
        }[options]
        assert result == expected

    def test_cat_enables_merge(self, options):
        c1, c2 = cu(t=(1, 2), z=1), cu(t=(3, 4, 5), z=1)
        c3, c4 = cu(t=(1, 2, 3), z=2), cu(t=(4, 5), z=2)
        c1234 = cu(t=(1, 2, 3, 4, 5), z=(1, 2))
        c12 = cu(t=(1, 2, 3, 4, 5), z=1)
        c34 = cu(t=(1, 2, 3, 4, 5), z=2)
        input_cubes = [c1, c2, c3, c4]
        result = combine_cubes(input_cubes, options)
        expected = {
            "legacy": input_cubes,
            "default": input_cubes,
            "recommended": [c12, c34],  # standard "mc" sequence can't do this one..
            "comprehensive": [c1234],  # .. but works if you repeat
        }[options]
        assert result == expected

    def test_cat_enables_merge__custom(self):
        c1, c2 = cu(t=(1, 2), z=1), cu(t=(3, 4, 5), z=1)
        c3, c4 = cu(t=(1, 2, 3), z=2), cu(t=(4, 5), z=2)
        c1234 = cu(t=(1, 2, 3, 4, 5), z=(1, 2))
        input_cubes = [c1, c2, c3, c4]
        result = combine_cubes(input_cubes, merge_concat_sequence="cm")
        assert result == [c1234]

    def test_nocombine_overlapping(self, options):
        c1, c2 = cu(t=(1, 3)), cu(t=(2, 4))
        input_cubes = [c1, c2]
        result = combine_cubes(input_cubes, options)
        assert result == input_cubes  # same in all cases : can't do this

    def test_nocombine_dim_scalar(self, options):
        c1, c2 = cu(t=(1,)), cu(t=2)
        input_cubes = [c1, c2]
        result = combine_cubes(input_cubes, options)
        assert result == input_cubes  # can't do this at present


class Test_api:
    """Check how combine options can be controlled, a variety of different ways."""

    @pytest.fixture(params=["unique", "nonunique"], autouse=True)
    def mergeunique(self, request):
        # We repeat each test with merge=True and merge=False.
        # The active option is stored on the test instance.
        self.merge_unique = request.param == "unique"
        yield

    def check_call(self, *args, **kwargs):
        def _capture_combine_inner(cubes, options, merge_require_unique):
            # A routine which replaces "_combine_cubes_inner" for interface testing.
            self.call_args = (options, merge_require_unique)

        cubes = []  # a dummy arg : we don't care about the cubes in these tests
        with mock.patch("iris.io.loading._combine_cubes_inner", _capture_combine_inner):
            combine_cubes(
                cubes, *args, merge_require_unique=self.merge_unique, **kwargs
            )

        return self.call_args

    def test_default(self, mergeunique):
        result = self.check_call()
        assert result == (LOAD_POLICY.settings(), self.merge_unique)

    def test_keys(self, mergeunique):
        assert LOAD_POLICY.settings()["repeat_until_unchanged"] is False
        result = self.check_call(repeat_until_unchanged=True)
        assert result[0]["repeat_until_unchanged"] is True

    def test_settings_name(self, mergeunique):
        result = self.check_call("comprehensive")
        expected = (LoadPolicy.SETTINGS["comprehensive"], self.merge_unique)
        assert result == expected

    def test_settings_name_withkeys(self, mergeunique):
        result = self.check_call("legacy", merge_concat_sequence="c")
        expected = LoadPolicy.SETTINGS["legacy"].copy()
        expected["merge_concat_sequence"] = "c"
        assert result == (expected, self.merge_unique)

    def test_dict(self, mergeunique):
        arg = LoadPolicy.SETTINGS["default"]
        arg["repeat_until_unchanged"] = True
        result = self.check_call(arg)
        assert result == (arg, self.merge_unique)

    def test_dict_withkeys(self, mergeunique):
        arg = LoadPolicy.SETTINGS["default"]
        assert arg["merge_concat_sequence"] == "m"
        arg["repeat_until_unchanged"] = True
        result = self.check_call(arg, merge_concat_sequence="c")
        expected = arg.copy()
        expected["merge_concat_sequence"] = "c"
        assert result == (expected, self.merge_unique)
