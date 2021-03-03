# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""
Unit tests for the :class:`iris.experimental.ugrid.MeshCoord`.

"""
# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests

import numpy as np
import unittest.mock as mock

from iris.cube import Cube
from iris.coords import AuxCoord, Coord
from iris.experimental.ugrid import Connectivity, Mesh, _fetch_mesh_coord

from iris.experimental.ugrid import MeshCoord

# Default test object creation controls
_TEST_N_NODES = 15
_TEST_N_FACES = 3
_TEST_N_EDGES = 5
_TEST_N_BOUNDS = 4

# Default actual points + bounds.
_TEST_POINTS = np.arange(_TEST_N_FACES)
_TEST_BOUNDS = np.arange(_TEST_N_FACES * _TEST_N_BOUNDS)
_TEST_BOUNDS = _TEST_BOUNDS.reshape((_TEST_N_FACES, _TEST_N_BOUNDS))


def _create_test_mesh():
    node_x = AuxCoord(
        1100 + np.arange(_TEST_N_NODES),
        standard_name="longitude",
        long_name="long-name",
        var_name="var",
    )
    node_y = AuxCoord(
        1200 + np.arange(_TEST_N_NODES), standard_name="latitude"
    )

    conns = np.arange(_TEST_N_EDGES * 2, dtype=int)
    conns = ((conns + 5) % _TEST_N_NODES).reshape((_TEST_N_EDGES, 2))
    edge_nodes = Connectivity(conns, cf_role="edge_node_connectivity")
    edge_x = AuxCoord(
        2100 + np.arange(_TEST_N_EDGES), standard_name="longitude"
    )
    edge_y = AuxCoord(
        2200 + np.arange(_TEST_N_EDGES), standard_name="latitude"
    )

    conns = np.arange(_TEST_N_FACES * _TEST_N_BOUNDS, dtype=int)
    conns = (conns % _TEST_N_NODES).reshape((_TEST_N_FACES, _TEST_N_BOUNDS))
    face_nodes = Connectivity(conns, cf_role="face_node_connectivity")
    face_x = AuxCoord(
        3100 + np.arange(_TEST_N_FACES), standard_name="longitude"
    )
    face_y = AuxCoord(
        3200 + np.arange(_TEST_N_FACES), standard_name="latitude"
    )

    mesh = Mesh(
        topology_dimension=2,
        node_coords_and_axes=[(node_x, "x"), (node_y, "y")],
        connectivities=[face_nodes, edge_nodes],
        edge_coords_and_axes=[(edge_x, "x"), (edge_y, "y")],
        face_coords_and_axes=[(face_x, "x"), (face_y, "y")],
    )
    return mesh


def _default_create_args():
    # Produce a minimal set of default constructor args
    kwargs = {"location": "face", "axis": "x", "mesh": _create_test_mesh()}
    # NOTE: *don't* include coord_system or climatology.
    # We expect to only set those (non-default) explicitly.
    return kwargs


def _create_test_meshcoord(**override_kwargs):
    kwargs = _default_create_args()
    # Apply requested overrides and additions.
    kwargs.update(override_kwargs)
    # Create and return the test coord.
    result = MeshCoord(**kwargs)
    return result


class Test___init__(tests.IrisTest):
    def setUp(self):
        self.meshcoord = _create_test_meshcoord()

    def test_basic(self):
        kwargs = _default_create_args()
        meshcoord = _create_test_meshcoord(**kwargs)
        for key, val in kwargs.items():
            self.assertEqual(getattr(meshcoord, key), val)
        self.assertIsInstance(meshcoord, MeshCoord)
        self.assertIsInstance(meshcoord, Coord)

    def test_derived_properties(self):
        # Check the derived properties of the meshcoord against the correct
        # underlying mesh coordinate.
        for axis in ("x", "y"):
            meshcoord = _create_test_meshcoord(axis=axis)
            # N.B.
            node_x_coords = meshcoord.mesh.coord(include_nodes=True, axis=axis)
            (node_x_coord,) = list(node_x_coords.values())
            for key in node_x_coord.metadata._fields:
                meshval = getattr(meshcoord, key)
                if key == "var_name":
                    # var_name is unused.
                    self.assertIsNone(meshval)
                else:
                    # names, units and attributes are derived from the node coord.
                    self.assertEqual(meshval, getattr(node_x_coord, key))

    def test_fail_bad_mesh(self):
        with self.assertRaisesRegex(ValueError, "must be a.*Mesh"):
            _create_test_meshcoord(mesh=mock.sentinel.odd)

    def test_valid_locations(self):
        for loc in ("face", "edge", "node"):
            meshcoord = _create_test_meshcoord(location=loc)
            self.assertEqual(meshcoord.location, loc)

    def test_fail_bad_location(self):
        with self.assertRaisesRegex(ValueError, "not a valid Mesh location"):
            _create_test_meshcoord(location="bad")

    def test_fail_bad_axis(self):
        with self.assertRaisesRegex(ValueError, "not a valid Mesh axis"):
            _create_test_meshcoord(axis="q")


class Test__readonly_properties(tests.IrisTest):
    def setUp(self):
        self.meshcoord = _create_test_meshcoord()

    def test_fixed_metadata(self):
        # Check that you cannot set any of these on an existing MeshCoord.
        meshcoord = self.meshcoord
        for prop in ("mesh", "location", "axis"):
            with self.assertRaisesRegex(AttributeError, "can't set"):
                setattr(meshcoord, prop, mock.sentinel.odd)

    def test_coord_system(self):
        # The property exists, =None, can set to None, can not set otherwise.
        self.assertTrue(hasattr(self.meshcoord, "coord_system"))
        self.assertIsNone(self.meshcoord.coord_system)
        self.meshcoord.coord_system = None
        with self.assertRaisesRegex(ValueError, "Cannot set.* MeshCoord"):
            self.meshcoord.coord_system = 1

    def test_set_climatological(self):
        # The property exists, =False, can set to False, can not set otherwise.
        self.assertTrue(hasattr(self.meshcoord, "climatological"))
        self.assertFalse(self.meshcoord.climatological)
        self.meshcoord.climatological = False
        with self.assertRaisesRegex(ValueError, "Cannot set.* MeshCoord"):
            self.meshcoord.climatological = True


class Test__points_and_bounds(tests.IrisTest):
    # TODO: expand tests for the calculated results, their properties and
    #  dynamic behaviour, when we implement dynamic calculations.
    # TODO: test with missing optional mesh elements, i.e. face/edge locations,
    #  when we support that.
    def test_node(self):
        meshcoord = _create_test_meshcoord(location="node")
        self.assertTrue(meshcoord.has_lazy_points())
        self.assertIsNone(meshcoord.core_bounds())
        self.assertArrayAllClose(
            meshcoord.points, 1100 + np.arange(_TEST_N_NODES)
        )

    def test_edge(self):
        meshcoord = _create_test_meshcoord(location="edge")
        self.assertTrue(meshcoord.has_lazy_points())
        self.assertTrue(meshcoord.has_lazy_bounds())
        points, bounds = meshcoord.core_points(), meshcoord.core_bounds()
        self.assertEqual(points.shape, meshcoord.shape)
        self.assertEqual(bounds.shape, meshcoord.shape + (2,))
        self.assertArrayAllClose(
            meshcoord.points, [2100, 2101, 2102, 2103, 2104]
        )
        self.assertArrayAllClose(
            meshcoord.bounds,
            [
                (1105, 1106),
                (1107, 1108),
                (1109, 1110),
                (1111, 1112),
                (1113, 1114),
            ],
        )

    def test_face(self):
        meshcoord = _create_test_meshcoord(location="face")
        self.assertTrue(meshcoord.has_lazy_points())
        self.assertTrue(meshcoord.has_lazy_bounds())
        points, bounds = meshcoord.core_points(), meshcoord.core_bounds()
        self.assertEqual(points.shape, meshcoord.shape)
        self.assertEqual(bounds.shape, meshcoord.shape + (4,))
        self.assertArrayAllClose(meshcoord.points, [3100, 3101, 3102])
        self.assertArrayAllClose(
            meshcoord.bounds,
            [
                (1100, 1101, 1102, 1103),
                (1104, 1105, 1106, 1107),
                (1108, 1109, 1110, 1111),
            ],
        )


class Test___eq__(tests.IrisTest):
    def setUp(self):
        self.mesh = _create_test_mesh()

    def _create_common_mesh(self, **kwargs):
        return _create_test_meshcoord(mesh=self.mesh, **kwargs)

    def test_same_mesh(self):
        meshcoord1 = self._create_common_mesh()
        meshcoord2 = self._create_common_mesh()
        self.assertEqual(meshcoord2, meshcoord1)

    def test_different_identical_mesh(self):
        # For equality, must have the SAME mesh (at present).
        mesh1 = _create_test_mesh()
        mesh2 = _create_test_mesh()  # Presumably identical, but not the same
        meshcoord1 = _create_test_meshcoord(mesh=mesh1)
        meshcoord2 = _create_test_meshcoord(mesh=mesh2)
        # These should NOT compare, because the Meshes are not identical : at
        # present, Mesh equality is not implemented (i.e. limited to identity)
        self.assertNotEqual(meshcoord2, meshcoord1)

    def test_different_location(self):
        meshcoord = self._create_common_mesh()
        meshcoord2 = self._create_common_mesh(location="node")
        self.assertNotEqual(meshcoord2, meshcoord)

    def test_different_axis(self):
        meshcoord = self._create_common_mesh()
        meshcoord2 = self._create_common_mesh(axis="y")
        self.assertNotEqual(meshcoord2, meshcoord)


class Test__copy(tests.IrisTest):
    def test_basic(self):
        meshcoord = _create_test_meshcoord()
        meshcoord2 = meshcoord.copy()
        self.assertIsNot(meshcoord2, meshcoord)
        self.assertEqual(meshcoord2, meshcoord)
        # In this case, they should share *NOT* copy the Mesh object.
        self.assertIs(meshcoord2.mesh, meshcoord.mesh)

    def test_fail_copy_newpoints(self):
        meshcoord = _create_test_meshcoord()
        with self.assertRaisesRegex(ValueError, "Cannot change the content"):
            meshcoord.copy(points=meshcoord.points)

    def test_fail_copy_newbounds(self):
        meshcoord = _create_test_meshcoord()
        with self.assertRaisesRegex(ValueError, "Cannot change the content"):
            meshcoord.copy(bounds=meshcoord.bounds)


class Test__getitem__(tests.IrisTest):
    def test_slice_wholeslice_1tuple(self):
        # The only slicing case that we support, to enable cube slicing.
        meshcoord = _create_test_meshcoord()
        meshcoord2 = meshcoord[
            :,
        ]
        self.assertIsNot(meshcoord2, meshcoord)
        self.assertEqual(meshcoord2, meshcoord)
        # In this case, we should *NOT* copy the linked Mesh object.
        self.assertIs(meshcoord2.mesh, meshcoord.mesh)

    def test_slice_whole_slice_singlekey(self):
        # A slice(None) also fails, if not presented in a 1-tuple.
        meshcoord = _create_test_meshcoord()
        with self.assertRaisesRegex(ValueError, "Cannot index"):
            meshcoord[:]

    def test_fail_slice_part(self):
        meshcoord = _create_test_meshcoord()
        with self.assertRaisesRegex(ValueError, "Cannot index"):
            meshcoord[:1]


class Test_cube_containment(tests.IrisTest):
    # Check that we can put a MeshCoord into a cube, and have it behave just
    # like a regular AuxCoord.
    def setUp(self):
        meshcoord = _create_test_meshcoord()
        data_shape = (2,) + _TEST_POINTS.shape
        cube = Cube(np.zeros(data_shape))
        cube.add_aux_coord(meshcoord, 1)
        self.meshcoord = meshcoord
        self.cube = cube

    def test_added_to_cube(self):
        meshcoord = self.meshcoord
        cube = self.cube
        self.assertIn(meshcoord, cube.coords())

    def test_cube_dims(self):
        meshcoord = self.meshcoord
        cube = self.cube
        self.assertEqual(meshcoord.cube_dims(cube), (1,))
        self.assertEqual(cube.coord_dims(meshcoord), (1,))

    def test_find_by_name(self):
        meshcoord = self.meshcoord
        cube = self.cube
        self.assertIs(cube.coord(standard_name="longitude"), meshcoord)
        self.assertIs(cube.coord(long_name="long-name"), meshcoord)
        # self.assertIs(cube.coord(var_name="var"), meshcoord)

    def test_find_by_axis(self):
        meshcoord = self.meshcoord
        cube = self.cube
        self.assertIs(cube.coord(axis="x"), meshcoord)
        self.assertEqual(cube.coords(axis="y"), [])

        # NOTE: the meshcoord.axis takes precedence over the older
        # "guessed axis" approach.  So the standard_name does not control it.
        meshcoord.rename("latitude")
        self.assertIs(cube.coord(axis="x"), meshcoord)
        self.assertEqual(cube.coords(axis="y"), [])

    def test_cube_copy(self):
        # Check that we can copy a cube, and get a MeshCoord == the original.
        # Note: currently must have the *same* mesh, as for MeshCoord.copy().
        meshcoord = self.meshcoord
        cube = self.cube
        cube2 = cube.copy()
        meshco2 = cube2.coord(meshcoord)
        self.assertIsNot(meshco2, meshcoord)
        self.assertEqual(meshco2, meshcoord)

    def test_cube_nonmesh_slice(self):
        # Check that we can slice a cube on a non-mesh dimension, and get a
        # meshcoord == original.
        # Note: currently this must have the *same* mesh, as for .copy().
        meshcoord = self.meshcoord
        cube = self.cube
        cube2 = cube[:1]  # Make a reduced copy, slicing the non-mesh dim
        meshco2 = cube2.coord(meshcoord)
        self.assertIsNot(meshco2, meshcoord)
        self.assertEqual(meshco2, meshcoord)

    def test_cube_mesh_partslice(self):
        # Check that we can *not* get a partial MeshCoord slice, as the
        # MeshCoord refuses to be sliced.
        # Instead, you get an AuxCoord created from the MeshCoord.
        meshcoord = self.meshcoord
        cube = self.cube
        cube2 = cube[:, :1]  # Make a reduced copy, slicing the mesh dim

        # The resulting coord can not be identified with the original.
        # (i.e. metadata does not match)
        co_matches = cube2.coords(meshcoord)
        self.assertEqual(co_matches, [])

        # The resulting coord is an AuxCoord instead of a MeshCoord, but the
        # values match.
        co2 = cube2.coord(meshcoord.name())
        self.assertFalse(isinstance(co2, MeshCoord))
        self.assertIsInstance(co2, AuxCoord)
        self.assertArrayAllClose(co2.points, meshcoord.points[:1])
        self.assertArrayAllClose(co2.bounds, meshcoord.bounds[:1])


class Test_auxcoord_conversion(tests.IrisTest):
    def test_basic(self):
        meshcoord = _create_test_meshcoord()
        auxcoord = AuxCoord.from_coord(meshcoord)
        for propname, auxval in auxcoord.metadata._asdict().items():
            meshval = getattr(meshcoord, propname)
            self.assertEqual(auxval, meshval)
        # Also check array content.
        self.assertArrayAllClose(auxcoord.points, meshcoord.points)
        self.assertArrayAllClose(auxcoord.bounds, meshcoord.bounds)


#
# Testing for dynamic views + behaviour :
#   * missing-points handling, i.e. non-square faces (or similar)
#   * dynamic action (fetch from Mesh at compute time)
#   *
#
# BIG, BIG PROBLEM FOUND :
#   *** True dynamic action implies nested compute() calls. ***
#   *** we can't do this.
#   *** See :
#   ***    * https://github.com/SciTools/iris/issues/3237
#   ***    * https://github.com/SciTools/iris/pull/3255
#


class Test_MeshCoord__dataviews(tests.IrisTest):
    def setUp(self):
        # Construct a miniature face+nodes mesh for testing.
        face_nodes_array = np.array(
            [
                [0, 2, 1, 3],
                [1, 3, 10, 13],
                [2, 7, 9, 19],
                [
                    3,
                    4,
                    7,
                    -1,
                ],  # This one has a "missing" point (it's a triangle)
                [8, 1, 7, 2],
            ]
        )
        # Connectivity uses *masked* for missing points.
        face_nodes_array = np.ma.masked_less(face_nodes_array, 0)
        n_faces = face_nodes_array.shape[0]
        n_nodes = int(face_nodes_array.max() + 1)
        face_xs = 500.0 + np.arange(n_faces)
        node_xs = 100.0 + np.arange(n_nodes)

        # Record all these for re-use in tests
        self.n_faces = n_faces
        self.n_nodes = n_nodes
        self.face_xs = face_xs
        self.node_xs = node_xs
        self.face_nodes_array = face_nodes_array

        # Build a mesh with this info stored in it.

        co_nodex = AuxCoord(
            node_xs, standard_name="longitude", long_name="node_x", units=1
        )
        co_facex = AuxCoord(
            face_xs, standard_name="longitude", long_name="face_x", units=1
        )
        # N.B. the Mesh requires 'Y's as well.
        co_nodey = co_nodex.copy()
        co_nodey.rename("latitude")
        co_nodey.long_name = "node_y"
        co_facey = co_facex.copy()
        co_facey.rename("latitude")
        co_facey.long_name = "face_y"

        face_node_conn = Connectivity(
            face_nodes_array,
            cf_role="face_node_connectivity",
            long_name="face_nodes",
        )

        self.mesh = Mesh(
            topology_dimension=2,
            node_coords_and_axes=[(co_nodex, "x"), (co_nodey, "y")],
            connectivities=[face_node_conn],
            face_coords_and_axes=[(co_facex, "x"), (co_facey, "y")],
        )

        # Construct the new meshcoord.
        meshcoord = MeshCoord(mesh=self.mesh, location="face", axis="x")
        self.meshcoord = meshcoord

    # def assertArraysMaskedAllClose(self, arr1, arr2, fill=-999.0):
    #     # Test 2 arrays for ~equal values, including matching any NaNs.
    #     wherenans = np.isnan(arr1)
    #     self.assertArrayAllClose(np.isnan(arr2), wherenans)
    #     arr1 = np.where(wherenans, fill, arr1)
    #     arr2 = np.where(wherenans, fill, arr2)
    #     self.assertArrayAllClose(arr1, arr2)
    #
    def test_points_values(self):
        # Basic points content check.
        meshcoord = self.meshcoord
        self.assertTrue(meshcoord.has_lazy_points())
        # The points are just the face_x-s
        self.assertArrayAllClose(meshcoord.points, self.face_xs)

    def test_bounds_values(self):
        # Basic bounds content check.
        mesh_coord = self.meshcoord
        self.assertTrue(mesh_coord.has_lazy_bounds())
        # The bounds are selected node_x-s :  all == node_number + 100.0
        result = mesh_coord.bounds
        # N.B. result should be masked where the masked indices are.
        expected = 100.0 + self.face_nodes_array
        # Check there are *some* masked points.
        self.assertTrue(np.count_nonzero(expected.mask) > 0)
        # Check results match, including masked points.
        self.assertMaskedArrayAlmostEqual(result, expected)

    def test_points_deferred_access(self):
        # Check that MeshCoord.points always fetches from the current "face_x"
        # coord in the cube.
        mesh = self.mesh
        mesh_coord = self.meshcoord
        fetch_without_realise = mesh_coord.lazy_points().compute()
        all_points_vals = self.face_xs
        self.assertArrayAllClose(fetch_without_realise, all_points_vals)

        # Replace 'face_x' coord with one having different values, same name
        face_x_coord = _fetch_mesh_coord(mesh, "face", "x")
        face_x_coord_2 = face_x_coord.copy()
        face_x_coord_2.long_name = "face_x_2"
        all_points_vals_2 = np.array(
            all_points_vals + 1.0, dtype=int
        )  # Change both values and dtype.
        face_x_coord_2.points = all_points_vals_2
        mesh.remove_coords(include_faces=True, axis="x")
        mesh.add_coords(face_x=face_x_coord_2)

        # Check that new values + different dtype are now produced by the
        # MeshCoord bounds access.
        fetch_without_realise = mesh_coord.lazy_points().compute()
        self.assertArrayAllClose(fetch_without_realise, all_points_vals_2)
        self.assertEqual(fetch_without_realise.dtype, all_points_vals_2.dtype)
        self.assertNotEqual(fetch_without_realise.dtype, all_points_vals.dtype)

    # def test_bounds_deferred_access__node_x(self):
    #     # Show that MeshCoord.points always fetches from the current "node_x"
    #     # coord in the cube.
    #     cube = self.cube
    #     mesh_coord = self.mesh_coord
    #     fetch_without_realise = mesh_coord.lazy_bounds().compute()
    #     all_bounds_vals = array_index_with_missing(
    #         self.node_xs, self.face_nodes_array
    #     )
    #     self.assertArraysNanAllClose(fetch_without_realise, all_bounds_vals)
    #
    #     # Replace 'node_x' coord with one having different values, same name
    #     face_x_coord = self.cube.coord("node_x")
    #     face_x_coord_2 = face_x_coord.copy()
    #     all_face_points = face_x_coord.points
    #     all_face_points_2 = np.array(
    #         all_face_points + 1.0
    #     )  # Change the values.
    #     self.assertFalse(np.allclose(all_face_points_2, all_face_points))
    #     face_x_coord_2.points = all_face_points_2
    #     dims = cube.coord_dims(face_x_coord)
    #     cube.remove_coord(face_x_coord)
    #     cube.add_aux_coord(face_x_coord_2, dims)
    #
    #     # Check that new, different values are now delivered by the MeshCoord.
    #     expected_new_values = all_bounds_vals + 1.0
    #     fetch_without_realise = mesh_coord.lazy_bounds().compute()
    #     self.assertArraysNanAllClose(
    #         fetch_without_realise, expected_new_values
    #     )

    # def test_bounds_deferred_access__facenodes(self):
    #     # Show that MeshCoord.points always fetches from the current
    #     # "face_node_connectivity" coord in the cube.
    #     cube = self.cube
    #     mesh_coord = self.mesh_coord
    #     fetch_without_realise = mesh_coord.lazy_bounds().compute()
    #     all_bounds_vals = array_index_with_missing(
    #         self.node_xs, self.face_nodes_array
    #     )
    #     self.assertArraysNanAllClose(fetch_without_realise, all_bounds_vals)
    #
    #     # Replace the index coord with one having different values, same name
    #     face_nodes_coord = self.cube.coord("face_node_connectivity")
    #     face_nodes_coord_2 = face_nodes_coord.copy()
    #     conns = face_nodes_coord.bounds
    #     conns_2 = np.array(conns % 10)  # Change some values
    #     self.assertFalse(np.allclose(conns, conns_2))
    #     face_nodes_coord_2.bounds = conns_2
    #     dims = cube.coord_dims(face_nodes_coord)
    #     cube.remove_coord(face_nodes_coord)
    #     cube.add_aux_coord(face_nodes_coord_2, dims)
    #
    #     # Check that new + different values are now delivered by the MeshCoord.
    #     expected_new_values = self.node_xs[conns_2]
    #     fetch_without_realise = mesh_coord.lazy_bounds().compute()
    #     self.assertArrayAllClose(fetch_without_realise, expected_new_values)

    # def test_meshcoord_leaves_originals_lazy(self):
    #     cube = self.cube
    #
    #     # Ensure all the source coords are lazy.
    #     source_coords = ("face_x", "node_x", "face_node_connectivity")
    #     for name in source_coords:
    #         co = cube.coord(name)
    #         co.points = co.lazy_points()
    #         co.bounds = co.lazy_bounds()
    #
    #     # Check all the source coords are lazy.
    #     for name in source_coords:
    #         co = cube.coord(name)
    #         co.points = co.lazy_points()
    #         self.assertTrue(co.has_lazy_points())
    #         if co.has_bounds():
    #             self.assertTrue(co.has_lazy_bounds())
    #
    #     # Calculate both points + bounds of the meshcoord
    #     mesh_coord = self.mesh_coord
    #     self.assertTrue(mesh_coord.has_lazy_points())
    #     self.assertTrue(mesh_coord.has_lazy_bounds())
    #     mesh_coord.points
    #     mesh_coord.bounds
    #     self.assertFalse(mesh_coord.has_lazy_points())
    #     self.assertFalse(mesh_coord.has_lazy_bounds())
    #
    #     # Check all the source coords are still lazy.
    #     for name in source_coords:
    #         co = cube.coord(name)
    #         co.points = co.lazy_points()
    #         self.assertTrue(co.has_lazy_points())
    #         if co.has_bounds():
    #             self.assertTrue(co.has_lazy_bounds())


if __name__ == "__main__":
    tests.main()
