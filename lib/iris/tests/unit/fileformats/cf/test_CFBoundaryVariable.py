# Copyright Iris contributors
#
# This file is part of Iris and is released under the BSD license.
# See LICENSE in the root of the repository for full licensing details.
"""Unit tests for :class:`iris.fileformats.cf.CFBoundaryVariable`."""

from iris.fileformats.cf import CFBoundaryVariable

from .identify_mixins import (
    IdentifyByAttributeMixin,
    SpansMixin,
    _NetCDFVar,
)


class TestIdentify(IdentifyByAttributeMixin):
    __test__ = True

    CF_CLASS = CFBoundaryVariable
    CF_IDENTITIES = ["bounds"]
    IDENTITY_SUPPORTS_MULTIPLE_REFS = False
    MISSING_WARN_REGEX = r"Missing CF-netCDF boundary variable {subject!r}.*"


class TestSpans(SpansMixin):
    """Tests for CFBoundaryVariable.spans()."""

    __test__ = True
    CF_CLASS = CFBoundaryVariable
