# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""Integration tests for regridding of various MockCoord approaches."""

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests
from unittest import skip

import numpy as np

from iris.coords import AuxCoord, _DimensionalMetadata, Coord
from iris.cube import Cube
import iris.tests.stock as istk


# Types of regridding scheme to target:
from iris.analysis import (
    Linear,
    # Nearest,
    AreaWeighted,
    UnstructuredNearest,
    # PointInCell,
)


class MixinMockcoordRegridTests:
    # def test_auxcontent_unregridded(self):
    #     # Check the type of the coord seen in the original cube
    #     cube = self.source_cube_auxcontent_mock
    #     self._check_mockcoord_preservedtype(cube)
    #
    # def test_dimcontent_unregridded(self):
    #     # Check the type of the coord seen in the original cube
    #     cube = self.source_cube_dimcontent_mock
    #     self._check_mockcoord_preservedtype(cube)

    # *** Linear ***
    # Linear.regridder --> i.a._regrid.RectilinearRegridder
    #   --> i.a._interpolation.snapshot_grid -->  i.a._interpolation.get_xy_dim_coords
    # So it can't work over AuxCoords.
    # Aim to show that additional attached MockCoords are preserved / re-interpolated.
    @skip
    def test_auxcontent_linear(self):
        # Check the type of the coord seen in the original cube
        # THIS DOES NOT PRESERVE : throws away (does not regrid) aux-coords on horizontal dims
        # See: i.a._regrid.py:895
        cube = self.source_cube_auxcontent_mock
        cube = cube.regrid(self.target_cube, Linear())
        self._check_mockcoord_preservedtype(cube)

    # *** Nearest ***
    # Nearest.regridder --> i.a._regrid.RectilinearRegridder
    # So, just like the above : can only use DimCoords.
    # NOT WORTH DOING
    # def test_auxcontent_linear(self):
    #     # Check the type of the coord seen in the original cube
    #     cube = self.source_cube_auxcontent_mock
    #     cube = cube.regrid(self.target_cube, Nearest)
    #     _check_mockcoord_preservedtype(self, cube)

    # *** AreaWeighted ***
    # ALL THE SAME PROBLEMS : can't use AuxCoords.
    @skip
    def test_auxcontent_aw(self):
        # See: i.a._regrid.py:895
        source_cube = self.source_cube_auxcontent_mock.copy()
        source_cube.remove_coord("longitude")
        mock_coord = source_cube.coord("mock_x")
        mock_coord.rename("longitude")
        mock_coord.units = "degrees"
        target_cube = self.target_cube.copy()
        for cube in (source_cube, target_cube):
            for axis_name in ("x", "y"):
                coord = cube.coord(axis=axis_name)
                if coord.bounds is None:
                    coord.guess_bounds()
        result_cube = source_cube.regrid(target_cube, AreaWeighted())
        self._check_mockcoord_preservedtype(result_cube)

    # *** UnstructuredNearest ***
    def test_mocksource_unstructured_nearest(self):
        # This requires an X and Y coord on a common dimension (like a mesh dim).
        # See: i.a._regrid.py:895
        target_cube = self.target_cube.copy()

        # Use the coords in the test-provided source-cube as a template for new ones.
        co_lats = self.source_cube_auxcontent_mock.coord("latitude")
        co_mock = self.source_cube_auxcontent_mock.coord("mock_x")

        # Construct a test cube with a single mesh dimension, and two 1-D lats_lons coords.
        # But the 'lons' coord is of the MockCoord type.
        n_mesh = 8
        source_cube = Cube(np.arange(n_mesh, dtype=float))
        co_lats = co_lats.copy(
            np.linspace(0.0, 2.0, n_mesh)
        )  # Values cover some of the source lats range
        co_mock = co_mock.copy(
            np.linspace(0.0, 2.0, n_mesh)
        )  # Values cover some of the source lons range
        # Fix the newly-conceived mock coord to "look like" a longitude aux-coord.
        co_mock.rename("longitude")
        co_mock.units = "degrees"
        co_mock.coord_system = co_lats.coord_system
        # We also
        for co in (co_lats, co_mock):
            source_cube.add_aux_coord(co, 0)

        # No check : just "it doesn't fail".
        source_cube.regrid(target_cube, UnstructuredNearest())
        # The result will *NOT* have a MockCoord : regridding replaces it.
        # self._check_mockcoord_preservedtype(result_cube)

    # def test_mocktarget_unstructured_nearest(self):
    #     # This requires an X and Y coord on a common dimension (like a mesh dim).
    #     # See: i.a._regrid.py:895
    #     source_cube = self.source_cube_auxcontent_mock.copy()
    #     # Grab the additional 'mock' coord from the test source cube, and remove it.
    #     # We will use it as the type prototype for replacing
    #     mock_coord = source_cube.coord('mock_x')
    #     source_cube.remove_coord(mock_coord)
    #
    #     target_cube = self.target_cube.copy()
    #
    #     # Use the coords in the test-provided source-cube as a template for new ones.
    #     co_lats = self.source_cube_auxcontent_mock.coord('latitude')
    #     co_mock = self.source_cube_auxcontent_mock.coord('mock_x')
    #
    #     # Construct a test cube with a single mesh dimension, and two 1-D lats_lons coords.
    #     # But the 'lons' coord is of the MockCoord type.
    #     n_mesh = 8
    #     source_cube = Cube(np.arange(n_mesh, dtype=float))
    #     co_lats = co_lats.copy(np.linspace(0.0, 2.0, n_mesh))  # Values cover some of the source lats range
    #     co_mock = co_mock.copy(np.linspace(0.0, 2.0, n_mesh))  # Values cover some of the source lons range
    #     # Fix the newly-conceived mock coord to "look like" a longitude aux-coord.
    #     co_mock.rename('longitude')
    #     co_mock.units = 'degrees'
    #     co_mock.coord_system = co_lats.coord_system
    #     # We also
    #     for co in (co_lats, co_mock):
    #         source_cube.add_aux_coord(co, 0)
    #
    #     result_cube = source_cube.regrid(target_cube, UnstructuredNearest())
    #     # The result will *NOT* have a MockCoord : regridding replaces it.
    #     # self._check_mockcoord_preservedtype(result_cube)


class MockCoord(AuxCoord):
    pass


def make_testcubes(test_self, mockcoord_class):
    cube = istk.lat_lon_cube()
    ny, nx = cube.shape
    mock_co = mockcoord_class(np.arange(nx), long_name="mock_x", units=1)

    # The "auxcontent" version is the cube with an additional MockCoord.
    auxcube = cube.copy()
    auxcube.add_aux_coord(mock_co, 1)
    test_self.source_cube_auxcontent_mock = auxcube

    # Also define a suitable target grid.
    targetgrid = cube.copy()
    co_lat = targetgrid.coord("latitude")
    co_lon = targetgrid.coord("longitude")
    co_lat.points = co_lat.points + 0.5
    co_lon.points = co_lon.points + 0.5
    test_self.target_cube = targetgrid


class Mixin_AuxcoordbasedMockcoords:
    def _setup(self):
        make_testcubes(self, MockCoord)

    def _check_mockcoord_preservedtype(self, cube):
        mock_coords = [
            co
            for co in cube.coords()
            if any(
                "mock" in (getattr(co, keyname) or "")
                for keyname in ("long_name", "var_name")
            )
        ]
        self.assertEqual(len(mock_coords), 1)
        self.assertIsInstance(mock_coords[0], MockCoord)


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

    # We also need a "points" alias for the "values" array
    # CODE STOLEN + COPIED FROM COORD
    @property
    def points(self):
        """The coordinate points values as a NumPy array."""
        return self._values

    @points.setter
    def points(self, points):
        self._values = points


class MixinMinimalbasedMockcoord:
    def _setup(self):
        make_testcubes(self, MinimalCoordlikeDimmeta)

    def _check_mock_coord(self, cube):
        self.assertIsInstance(cube.coord("mock_x"), MinimalCoordlikeDimmeta)


#
# The actual TestCase classes.
# Mixins and 'setUp' wrappers needed, because of peculiar behaviour of unittest.TestCase with subclassing.
#


class Test_MockCoord(
    tests.IrisTest, Mixin_AuxcoordbasedMockcoords, MixinMockcoordRegridTests
):
    def setUp(self):
        Mixin_AuxcoordbasedMockcoords._setup(self)


class TestMimimalCoordlike(
    tests.IrisTest, MixinMinimalbasedMockcoord, MixinMockcoordRegridTests
):
    def setUp(self):
        MixinMinimalbasedMockcoord._setup(self)


if __name__ == "__main__":
    tests.main()
