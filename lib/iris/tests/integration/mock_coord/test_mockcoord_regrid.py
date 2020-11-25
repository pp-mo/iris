# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""Integration tests for regridding of various MockCoord approaches."""

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests

import numpy as np

from iris.coords import AuxCoord  # , _DimensionalMetadata, Coord
import iris.tests.stock as istk


# Types of regridding scheme to target:
from iris.analysis import (
    Linear,
    # Nearest,
    # UnstructuredNearest,
    # AreaWeighted,
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
    def test_auxcontent_linear(self):
        # Check the type of the coord seen in the original cube
        # THIS DOES NOT PRESERVE : throws away (does not regrid) aux-coords on horizontal dims
        # See: i.a._regrid.py:895
        cube = self.source_cube_auxcontent_mock
        cube = cube.regrid(self.target_cube, Linear())
        self._check_mockcoord_preservedtype(cube)

    # # *** Nearest ***
    # # Nearest.regridder --> i.a._regrid.RectilinearRegridder
    # # So, all as above.  Possibly not even worth doing?
    # def test_auxcontent_linear(self):
    #     # Check the type of the coord seen in the original cube
    #     cube = self.source_cube_auxcontent_mock
    #     cube = cube.regrid(self.target_cube, Nearest)
    #     _check_mockcoord_preservedtype(self, cube)


class MockCoord(AuxCoord):
    pass


class Test_MockCoord(tests.IrisTest, MixinMockcoordRegridTests):
    def setUp(self):
        cube = istk.lat_lon_cube()
        ny, nx = cube.shape
        mock_co = MockCoord(np.zeros(nx), long_name="mock_x", units=1)

        # The "auxcontent" version is the cube with an additional MockCoord.
        auxcube = cube.copy()
        auxcube.add_aux_coord(mock_co, 1)
        self.source_cube_auxcontent_mock = auxcube

        # The "dimcontent" version has a MockCoord **in place of** the original longitude coord,
        # and both lons + lats are AuxCoords.
        dimcube = cube.copy()
        co_lat = cube.coord("latitude")
        co_lon = cube.coord("longitude")
        dimcube.remove_coord(co_lon)
        dimcube.remove_coord(co_lat)
        dimcube.add_aux_coord(co_lat, 0)
        kwargs = {
            key: getattr(co_lon, key, None)
            for key in (
                "points",
                "bounds",
                "standard_name",
                "long_name",
                "var_name",
                "units",
                "attributes",
            )
        }
        co_lon2 = MockCoord(**kwargs)
        co_lon2.var_name = "mock_x"  # Still can identify with this
        dimcube.add_aux_coord(co_lon2, 1)
        self.source_cube_dimcontent_mock = dimcube

        # Also define a suitable target grid.
        targetgrid = cube.copy()
        co_lat = targetgrid.coord("latitude")
        co_lon = targetgrid.coord("longitude")
        co_lat.points = co_lat.points + 0.5
        co_lon.points = co_lon.points + 0.5
        self.target_cube = targetgrid

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


# class MinimalCoordlikeDimmeta(_DimensionalMetadata):
#     def __init__(self, *args, **kwargs):
#         # Implement a minimal constructor
#         # FOR NOW: just the _DimMeta properties (and behaviour)
#         super().__init__(*args, **kwargs)
#
#     def cube_dims(self, cube):
#         # This is abstract in _DimMeta, so we must provide it.
#         return cube.coord_dims(
#             self
#         )  # We should behave like a Coord in this respect.In
#
#     @property
#     def __class__(self):
#         # Fake the "isinstance" behaviour (for now).
#         return Coord
#
#
# class Test_MinimalCoordlikeDimmeta(
#     tests.IrisTest, MixinMockcoordOperationsTests
# ):
#     def setUp(self):
#         cube = istk.lat_lon_cube()
#         ny, nx = cube.shape
#         # Absolute minimal thing : not even a name
#         mock_co = MinimalCoordlikeDimmeta(np.zeros(nx), long_name="mock_x")
#         cube.add_aux_coord(mock_co, 1)
#         self.mock_co = mock_co
#         self.cube = cube
#
#     def _check_mock_coord(self, cube):
#         self.assertIsInstance(cube.coord("mock_x"), MinimalCoordlikeDimmeta)


if __name__ == "__main__":
    tests.main()
