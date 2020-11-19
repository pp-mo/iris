# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""Integration tests for cube html representation."""

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests

import numpy as np

from iris.coords import AuxCoord, _DimensionalMetadata, Coord
import iris.tests.stock as istk


class MixinMockcoordOperationsTests:
    def test_coord_present(self):
        # Check the type of the coord seen in the original cube
        cube = self.cube
        self._check_mock_coord(cube)

    def test_cube_copy(self):
        # Check the type of the coord in cube copy.
        cube = self.cube.copy()
        self._check_mock_coord(cube)

    def test_slice_all(self):
        # Check result of no-op slicing with ':'.
        cube = self.cube[:]
        self._check_mock_coord(cube)

    def test_slice_section_y(self):
        # Check result of slicing with a range of the non-mock dimension.
        cube = self.cube[1:3]
        self._check_mock_coord(cube)

    def test_slice_section_x(self):
        # Check result of slicing with a range of the non-mock dimension.
        cube = self.cube[:, 1:3]
        self._check_mock_coord(cube)

    def test_slice_collapse_y(self):
        # Check result of no-op slice.
        cube = self.cube[1]
        self._check_mock_coord(cube)

    def test_slice_collapse_x(self):
        # Check result of no-op slice.
        cube = self.cube[:, 1]
        self._check_mock_coord(cube)


class MockCoord(AuxCoord):
    pass


class Test_MockCoord(tests.IrisTest, MixinMockcoordOperationsTests):
    def setUp(self):
        cube = istk.lat_lon_cube()
        ny, nx = cube.shape
        mock_co = MockCoord(np.zeros(nx), long_name="mock_x", units=1)
        cube.add_aux_coord(mock_co, 1)
        self.cube = cube

    def _check_mock_coord(self, cube):
        self.assertIsInstance(cube.coord("mock_x"), MockCoord)


class MinimalCoordlikeDimmeta(_DimensionalMetadata):
    def __init__(self, *args, **kwargs):
        # Implement a minimal constructor
        # FOR NOW: just the _DimMeta properties (and behaviour)
        super().__init__(*args, **kwargs)

    def cube_dims(self, cube):
        # This is abstract in _DimMeta, so we must provide it.
        return cube.coord_dims(
            self
        )  # We should behave like a Coord in this respect.In

    @property
    def __class__(self):
        # Fake the "isinstance" behaviour (for now).
        return Coord


class Test_MinimalCoordlikeDimmeta(
    tests.IrisTest, MixinMockcoordOperationsTests
):
    def setUp(self):
        cube = istk.lat_lon_cube()
        ny, nx = cube.shape
        # Absolute minimal thing : not even a name
        mock_co = MinimalCoordlikeDimmeta(np.zeros(nx), long_name="mock_x")
        cube.add_aux_coord(mock_co, 1)
        self.mock_co = mock_co
        self.cube = cube

    def _check_mock_coord(self, cube):
        self.assertIsInstance(cube.coord("mock_x"), MinimalCoordlikeDimmeta)


if __name__ == "__main__":
    tests.main()
