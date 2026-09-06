# Copyright Iris contributors
#
# This file is part of Iris and is released under the BSD license.
# See LICENSE in the root of the repository for full licensing details.
"""Unit tests for :class:`iris.fileformats.cf.CFClimatologyVariable`."""

from iris.fileformats.cf import CFClimatologyVariable

from .identify_mixins import (
    IdentifyByAttributeMixin,
    SpansMixin,
    _NetCDFVar,
)


class TestIdentify(IdentifyByAttributeMixin):
    __test__ = True

    CF_CLASS = CFClimatologyVariable
    CF_IDENTITIES = ["climatology"]
    IDENTITY_SUPPORTS_MULTIPLE_REFS = False
    MISSING_WARN_REGEX = r"Missing CF-netCDF climatology variable {subject!r}.*"


class TestSpans(SpansMixin):
    """Tests for CFClimatologyVariable.spans()."""

    __test__ = True
    CF_CLASS = CFClimatologyVariable
