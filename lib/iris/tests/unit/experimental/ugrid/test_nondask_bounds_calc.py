import iris.tests as tests

from collections import Iterable
import dask.array as da
import netCDF4 as nc
import numpy as np

from iris.coords import AuxCoord
from iris.fileformats.netcdf import NetCDFDataProxy

from test_meshcoord__dataview import ArrayMimic


def fetch_part_array_bysections(array, keys, section_size):
    """
    Efficiently fetch a sub-indexed part of a (potentially) large array.

    Implements a chunking-like access, without using Dask.
    The point of this is so that (a) the chunking is dynamic, (b) we can use it inside a Dask compute() call.
    That means we can use this to apply lazily-fetched indices to data :  Dask cannot do this efficiently, because
    it does not do dynamic chunking.

    We apply our specialist method *only* when the first key is a list/array of indices. Then :
    It divides the array into 'chunks' in its first dimension, and fetches only those chunks which are required for the
    given input indices, and only a minimal contiguous section of each chunk.
    This is really intended for efficient access to cf-vars, which might be very large
    ( and so can also be applied to NetCDFDataProxy-s ).

    This mechanism should work well, in principle, when the set of required indices is smallish but irregular.
    - i.e. the result is a relatively small fraction of the whole array, but it is not a simple subset (like a slice).
    E.G. this is exactly what would be expected when fetching data on a (relatively small) set of adjoining faces,
    or the nodes which are their bounds.

    Notes:
    * code is much complicated by supporting multiple indices.
      There is probably some way this can be made much simpler.
    * does nothing sensible with the extra indices : We assume these dims are relative small, and faster-varying
      (as in C-ordered array storage).  This should suit face-node-connectivity arrays.
    * does not yet handle out-of-range or missing indices.  Too-large indices currently cause errors.

    """
    if not isinstance(keys, tuple):
        keys = (keys,)
    dim0_key, rest_keys = keys[0], keys[1:]
    if isinstance(dim0_key, Iterable) and not isinstance(dim0_key, slice):
        # We have a bunch of indices in the first dimension.
        # We work out which "sections" of the array that this touches, and fetch only those.
        ind0s = np.array(dim0_key, dtype=int)
        result_shape = ind0s.shape + array.shape[1:]
        ind0s_flat = ind0s.flatten()
        flatresult_shape = ind0s_flat.shape + array.shape[1:]
        result = np.empty(flatresult_shape, dtype=array.dtype)
        ind0_sections = ind0s_flat // section_size
        ind0s_insection = ind0s_flat % section_size
        i_sections = set(ind0_sections.flatten())
        for i_sec in i_sections:
            # Work out which result slots are filled from this section.
            these_inds = np.where(ind0_sections == i_sec)[0]
            ind0s_this_section = ind0s_insection[these_inds]
            # Calculate the minimal contiguous slice of section required.
            sect_minind = min(ind0s_this_section)
            sect_maxind = max(ind0s_this_section)
            sect_start = (i_sec * section_size) + sect_minind
            sect_end = (i_sec * section_size) + sect_maxind + 1

            # *THIS* is the actual var access, typically via a "Dataproxy" so the file need not be open.
            one_section = array[sect_start:sect_end]
            # NOTE: here we are not passing keys beyond the first dimension.
            # - that is because this can be highly inefficient for netcdf variable access.
            # Instead we fetch a whole, presumably file-contiguous, chunk.
            # Parts of that may be extracted by "rest_keys" subsequently.
            # - this may cost more memory but is much quicker (in our specific cases : connectivity arrays)

            section_array_keys = (
                tuple([ind0s_this_section - sect_minind]) + rest_keys
            )
            results_array_keys = tuple([these_inds]) + rest_keys
            result[results_array_keys] = one_section[section_array_keys]
        result = result.reshape(result_shape)  # Unflatten the first dim
    else:
        # slice or single-value key : Just do the normal thing.
        result = array[keys]

    return result


def dataproxy_from_ncvar(var, filepath):
    """Create a NetCDFDataProxy for this 'var', from nc dataset in 'filepath'."""
    fill_value = getattr(
        var, "_FillValue", nc.default_fillvals[var.dtype.str[1:]]
    )
    dataproxy = NetCDFDataProxy(
        shape=var.shape,
        dtype=var.dtype,
        path=filepath,
        variable_name=var.name,
        fill_value=fill_value,
    )
    return dataproxy


class TestBoundsCalc(tests.IrisTest):
    def setUp(self):
        # Create an AuxCoord to demonstrate the non-Dask MeshCoord-bounds calculation.

        # Snapshot key variables from a testdata file + create data-proxies.
        filepath = tests.get_data_path(
            ("NetCDF", "unstructured_grid", "data_C4.nc")
        )
        ds = nc.Dataset(filepath)
        v_node_x = ds.variables["node_lon"]
        nodex_dtype = v_node_x.dtype
        nodex_units = v_node_x.units
        v_face_nodes = ds.variables["face_nodes"]
        face_nodes_startindex = v_face_nodes.start_index
        n_faces = v_face_nodes.shape[0]
        n_bounds = v_face_nodes.shape[1]
        # n_nodes = v_node_x.shape[0]
        dataproxy_node_x = dataproxy_from_ncvar(v_node_x, filepath)
        dataproxy_face_nodes = dataproxy_from_ncvar(v_face_nodes, filepath)
        ds.close()

        # Construct the meshcoord as an AuxCoord with specific lazy points + bounds.
        SECTIONS_SIZE = 10  # Use quite small section for debugging.  More typically 100k-10M ?

        # function for 'meshcoord' points-like calculation
        def points_calc(keys):
            # CHEAT with the points.
            # We don't actually have the correct info (face-x) in this file, so just return some node indices.
            some_node_inds = fetch_part_array_bysections(
                array=dataproxy_face_nodes,
                keys=keys + (0,),  # Just get the #0 corner of each face
                section_size=SECTIONS_SIZE,
            )

            return some_node_inds

        # Create a lazy points array for the coord.
        points_arraylike = ArrayMimic(
            access_func=points_calc, shape=(n_faces,), dtype=nodex_dtype
        )
        lazy_points = da.from_array(
            points_arraylike,
            chunks=-1,
            meta=np.ndarray,  # Avoid 0-size accesses from Dask characterisation
        )

        # function for 'meshcoord' bounds calculation
        def bounds_calc(keys):
            node_inds = fetch_part_array_bysections(
                dataproxy_face_nodes, keys=keys, section_size=SECTIONS_SIZE
            )
            node_inds = node_inds - face_nodes_startindex
            face_bounds = fetch_part_array_bysections(
                dataproxy_node_x, keys=(node_inds,), section_size=SECTIONS_SIZE
            )

            return face_bounds

        # Create a lazy bounds array for the coord.
        bounds_arraylike = ArrayMimic(
            access_func=bounds_calc,
            shape=(n_faces, n_bounds),
            dtype=nodex_dtype,
        )
        lazy_bounds = da.from_array(
            bounds_arraylike,
            chunks=-1,
            meta=np.ndarray,  # Avoid 0-size accesses from Dask characterisation
        )

        # Create the test coord with the lazy points + bounds calculations.
        mesh_coord = AuxCoord(
            points=lazy_points,
            bounds=lazy_bounds,
            long_name="face_x",
            units=nodex_units,
        )
        self.mesh_coord = mesh_coord

    def test_points(self):
        mesh_coord = self.mesh_coord
        # part = mesh_coord[1:4]
        part = mesh_coord[
            [12, 0, 17, 26],
        ]  # Note: form must be [inds,]; inds in array or list, *NOT* tuple
        points = part.points

        # Not a real test, but show operation succeeds + snapshot a sample result (which looks ok so far).
        self.assertArrayAllClose(
            points, [90, 5, 22, 31]  # we faked the points with node indices
        )

    def test_bounds(self):
        mesh_coord = self.mesh_coord
        part = mesh_coord[
            [2, 3, 76, 75],
        ]
        bounds = part.bounds

        # Not a real test, but show operation succeeds + snapshot a sample result (which looks ok so far).
        self.assertArrayAllClose(
            bounds,
            [
                [0.0, 22.5, 22.5, 0.0],
                [22.5, 45.0, 45.0, 22.5],
                [22.5, 45.0, 67.5, 45.0],
                [180.0, 135.0, 157.5, 180.0],
            ],
        )


if __name__ == "__main__":
    tests.run()
