# (C) British Crown Copyright 2013, Met Office
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
Support for conservative regridding via ESMPy.

"""

import numpy as np
# Import ESMF via iris.proxy, just so we can build the docs with no ESMF.
import iris.proxy
iris.proxy.apply_proxy('ESMF', globals())

import cartopy.crs as ccrs
import iris
import iris.experimental.regrid as i_regrid

import iris.experimental._angle_calcs as angle_calcs

#: A static Cartopy Geodetic() instance for transforming to true-lat-lons.
_CRS_TRUELATLON = ccrs.Geodetic()


def _convert_latlons(crs, x_array, y_array):
    """
    Convert x+y coords in a given crs to (x,y) values in true-lat-lons.

    .. note::

        Uses a plain Cartopy Geodetic to convert to true-lat-lons.  This makes
        no allowance for a non-spherical earth.  But then, neither does ESMF.

    """
    ll_values = _CRS_TRUELATLON.transform_points(crs, x_array, y_array)
    return ll_values[..., 0], ll_values[..., 1]


def _make_esmpy_field(x_coord, y_coord, ref_name='field',
                     data=None, mask=None):
    """
    Create an ESMPy ESMF.Field on given coordinates, based on a ESMF.Mesh.

    Create a ESMF.Mesh from the coordinates, defining corners and centre
    positions as lats+lons.
    Add a grid mask if provided.
    Create and return a Field mapped on this Mesh, setting data if provided.

    Args:

    * x_coord, y_coord (:class:`iris.coords.Coord`):
        Two-dimensional coordinates of shape (ny, nx).
        Their contiguous bounds define an ESMF.Mesh of shape (nx, ny).

    Kwargs:

    * data (:class:`numpy.ndarray`, shape (nx,ny)):
        Set the Field data content.
    * mask (:class:`numpy.ndarray`, boolean, shape (nx,ny)):
        Add a mask item to the grid, assigning it 0/1 where mask=False/True.

    """
    # Get all cell corner coordinates as true-lat-lons

#    x_bounds, y_bounds = np.meshgrid(x_coord.contiguous_bounds(),
#                                     y_coord.contiguous_bounds())
    ny, nx = x_coord.shape
    n_cells = nx * ny

    grid_crs = x_coord.coord_system.as_cartopy_crs()
    lon_bounds, lat_bounds = _convert_latlons(grid_crs,
                                              x_coord.bounds.flat[:],
                                              y_coord.bounds.flat[:])

    lon_bounds = lon_bounds.reshape((n_cells, 4))
    lat_bounds = lat_bounds.reshape((n_cells, 4))

    # Fix lon_bounds to avoid +/-180 crossing within each cell boundary.
    angle_calcs.fix_longitude_bounds(lon_bounds)

    # Calculate which cells are 'valid' (in ESMF terms, at least).
    i_ok = angle_calcs.valid_bounds_shapes(lon_bounds, lat_bounds)

    # Convert to a valid-indices array (for now -- for older code approach).
    i_ok = np.array(np.where(i_ok)[0])
    n_validpoints = i_ok.size

    lon_bounds = lon_bounds[i_ok]
    lat_bounds = lat_bounds[i_ok]

    assert np.all(angle_calcs.valid_bounds_shapes(lon_bounds, lat_bounds))

    # Make an index of the valid-node numbers from the original points
    # So.. nnfp[original_point_index] = index-in-valid-bounds-arrays
    # BECAUSE so-called 'nodeIds' argument to Mesh.add_nodes is actually *NOT*
    # node ids, but indices within the passed nodes array. *AND* all nodes
    # defined must be used in some element, or it complains.  Yuck !!
    node_numbers_from_points = np.zeros(n_cells * 4, dtype=np.int32)
    # fill blank slots with -1 (an invalid index value)
    node_numbers_from_points[:] = -1
    # define valid slots
    valid_node_inds = i_ok * 4
    for i_pt in range(4):
        node_numbers_from_points[i_pt + 4 * i_ok] = i_pt + 4 * np.arange(n_validpoints, dtype=np.int32)


    # create a Mesh object
    mesh = ESMF.Mesh(parametricDim=2, spatialDim=2)

    #
    # Create 'nodes' which represent the cell bounds points
    #
    # Create a map of 'id' number (integers) for all the bounds points
    # NOTE: these are the VALID points only...
    n_nodes = lon_bounds.size
    node_ids = np.arange(n_nodes, dtype=np.int32)
    # Create a map of all-zeros for the 'node owners' field
    node_owners = np.zeros(n_nodes)
    # Concatenate all the bounds position coords
    combined_node_coords = np.concatenate((lon_bounds[..., None],
                                           lat_bounds[..., None]),
                                          axis=-1).flat[:]

    mesh.add_nodes(nodeCount=n_nodes,
                   nodeIds=node_ids.flat[:],
                   nodeCoords=combined_node_coords,
                   nodeOwners=node_owners)


    #
    # Create 'elements', which represent the cells themselves
    #
    # order elements in our own way = (y, x) ordered
    n_elems = n_validpoints
    elem_ids = np.arange(n_elems, dtype=np.int32)

    # all are 'QUAD' type - i.e. have 4 corners in 2D
    elem_types = np.ones(n_elems, dtype=np.int32) * ESMF.MeshElemType.QUAD

    # define the connects...
    bounds_indices = np.arange(n_cells * 4, dtype=np.int32)
    bounds_indices = bounds_indices.reshape((n_cells, 4))
    # remove the invalid ones
    bounds_indices = bounds_indices[i_ok]
    # replace these indices with equivalent valid indices
    elem_connects = node_numbers_from_points[bounds_indices]
    # these should all be *valid* ones
    assert not np.any(elem_connects < 0)

    # Add a mask item to the Mesh, if requested
    if mask is not None:
        mask = None
#        mask = np.where(mask, 1, 0)
#        mask = np.array(mask, dtype=np.int32)
#        mask = mask.flat[:]

    mesh.add_elements(elementCount=n_elems,
                      elementIds=elem_ids.flat[:],
                      elementTypes=elem_types.flat[:],
                      elementConn=elem_connects.flat[:],
                      elementMask=mask)

    # create a Field based on this mesh
    field = ESMF.Field(mesh, ref_name, meshloc=ESMF.MeshLoc.ELEMENT)

    # assign data content, if provided
    if data is not None:
        field.data[:] = data.reshape(n_cells)[i_ok]

    return field


def regrid_conservative_via_esmpy(source_cube, grid_cube):
    """
    Perform a conservative regridding with ESMPy.

    Regrids the data of a source cube onto a new grid defined by a destination
    cube.

    Args:

    * source_cube (:class:`iris.cube.Cube`):
        Source data.
        Must have two identifiable horizontal dimension coordinates, which have
        bounds, and share a coordinate system.  These may be 1D or 2D.
        Must not contain any coordinate factories for horizontal coordinates.
    * grid_cube (:class:`iris.cube.Cube`):
        Defines the target horizontal grid:
        Must have two identifiable horizontal dimension coordinates, which have
        bounds, and share a coordinate system.  These may be 1D or 2D.
        Only the horizontal dimension coordinates are actually used.

    Returns:
        A new cube derived from source_cube, regridded onto the specified
        horizontal grid.

    Any additional coordinates which map onto the horizontal dimensions are
    removed, while all other metadata is retained.

    .. note::

        Both source and destination cubes must have two horizontal coordinates
        identified with the axes 'X' and 'Y'.
        The source and destination grids are both defined by the bounds of the
        horizontal coordinates, which must exist.
        The X and Y coords must have the same coord_system, and this must also
        possess a matching Cartopy CRS.

    .. note::

        Initialises the ESMF Manager, if it was not already called.
        This implements default Manager operations (e.g. logging).

        To alter this, make a prior call to ESMF.Manager().

    """

    # Get source + target XY coordinate pairs and check they are suitable.
    src_coords = i_regrid._get_xy_coords_1d_or_2d(source_cube)
    dst_coords = i_regrid._get_xy_coords_1d_or_2d(grid_cube)
    src_cs = src_coords[0].coord_system
    grid_cs = dst_coords[0].coord_system
    if src_cs is None or grid_cs is None:
        raise ValueError("Both 'src' and 'grid' Cubes must have a"
                         " coordinate system for their rectilinear grid"
                         " coordinates.")

    if src_cs.as_cartopy_crs() is None or grid_cs.as_cartopy_crs() is None:
        raise ValueError("Both 'src' and 'grid' Cubes coord_systems must have "
                         "a valid associated Cartopy CRS.")

    def _valid_units(coord):
        if isinstance(coord.coord_system, (iris.coord_systems.GeogCS,
                                           iris.coord_systems.RotatedGeogCS)):
            valid_units = 'degrees'
        else:
            valid_units = 'm'
        return coord.units == valid_units

    # Check that the grid coords have sensible units.
    if not all(_valid_units(coord) for coord in src_coords + dst_coords):
        raise ValueError("Unsupported units: must be 'degrees' or 'm'.")

    # Work out the dimensions occupoed by the horizontal coordinates
    def xy_dims(cube, xy_coords):
        if xy_coords[0].ndim == 1:
            # 1d X and Y occupy two separate source dimensions
            xy_dims = [cube.coord_dims(coord)[0]
                           for coord in src_coords]
        else:
            # 2d X and Y *share* two source dimensions.
            xy_dims = source_cube.coord_dims(src_coords[0])
        return xy_dims

    src_dims_xy = xy_dims(source_cube, src_coords)
    dst_dims_xy = xy_dims(grid_cube, dst_coords)

    # Check that the source has no aux-factories for horizontal coordinates.
    for factory in source_cube.aux_factories:
        for coord in factory.dependencies.itervalues():
            if coord is None:
                continue
            dims = source_cube.coord_dims(coord)
            if set(dims) & set(src_dims_xy):
                raise ValueError("Source cube for conservative regrid can not "
                                 "include coordinate factories operating over "
                                 "the horizontal dimensions.")

    # Initialise the ESMF manager in case it was not already done.
    ESMF.Manager(logkind=ESMF.LogKind.SINGLE)

    # Create a data array for the output cube.
    # Size matches source, except for X+Y dimensions
    dst_shape = np.array(source_cube.shape)
    dst_shape[list(src_dims_xy)] = [grid_cube.shape[i_dim]
                                    for i_dim in dst_dims_xy]
#    dst_shape = grid_cube.shape

    # NOTE: result_cube array is masked -- fix this afterward if all unmasked
    fullcube_data = np.ma.zeros(dst_shape)

#    if 1:
    # Iterate 2d slices over all possible indices of the 'other' dimensions
    all_other_dims = filter(lambda i_dim: i_dim not in src_dims_xy,
                            xrange(source_cube.ndim))
    all_combinations_of_other_inds = np.ndindex(*dst_shape[all_other_dims])
    for other_indices in all_combinations_of_other_inds:
        # Construct a tuple of slices to address the 2d xy field
        slice_indices_array = np.array([slice(None)] * source_cube.ndim)
        slice_indices_array[all_other_dims] = other_indices
        slice_indices_tuple = tuple(slice_indices_array)

        # Get the source data, reformed into the right dimension order, (x,y).
        src_data_2d = source_cube.data[slice_indices_tuple]
#        if (src_dims_xy[0] > src_dims_xy[1]):
#            src_data_2d = src_data_2d.transpose()

#        assert source_cube.ndim == 2
#        # NB must transpose data, as we have (y, x) dims order
#        #    (well usually, *not checked here*)
#        # .. but ESMF uses (x, y)
#        src_data_2d = source_cube.data.copy()

        # Work out whether we have missing data to define a source grid mask.
        if np.ma.is_masked(src_data_2d):
            srcdata_mask = np.ma.getmask(src_data_2d)
        else:
            srcdata_mask = None

        # Construct ESMF Field objects on source and destination grids.
        src_field = _make_esmpy_field(src_coords[0], src_coords[1],
                                      data=src_data_2d, mask=srcdata_mask)

        dst_field = _make_esmpy_field(dst_coords[0], dst_coords[1])

        # Make Field for destination coverage fraction (for missing data calc).
        coverage_field = _make_esmpy_field(dst_coords[0], dst_coords[1])

        # Do the actual regrid with ESMF.
        mask_flag_values = np.array([1], dtype=np.int32)
        regrid_method = ESMF.Regrid(src_field, dst_field,
                                    src_mask_values=mask_flag_values,
                                    regrid_method=ESMF.RegridMethod.CONSERVE,
                                    unmapped_action=ESMF.UnmappedAction.IGNORE,
                                    dst_frac_field=coverage_field)
        regrid_method(src_field, dst_field)
        data = dst_field.data

        # Convert destination 'coverage fraction' into a missing-data mask.
        # Set = wherever part of cell goes outside source grid, or overlaps a
        # masked source cell.
        coverage_tolerance_threshold = 1.0 - 1.0e-8
        data.mask = coverage_field.data < coverage_tolerance_threshold

        # Reconstruct proper shape (Iris-dims order)
        ny, nx = dst_coords[0].points.shape
        data = data.reshape((ny, nx))

        # Transpose ESMF result_cube dims (X,Y) back to the order of the source
        if (dst_dims_xy[0] > dst_dims_xy[1]):
            data = data.transpose()

        # Paste regridded slice back into parent array
        fullcube_data[slice_indices_tuple] = data

    # Remove the data mask if completely unused.
    if not np.ma.is_masked(fullcube_data):
        fullcube_data = np.array(fullcube_data)

#    # Generate a full 2d sample grid, as required for regridding orography
#    # NOTE: as seen in "regrid_bilinear_rectilinear_src_and_grid"
#    # TODO: can this not also be wound into the _create_cube method ?
#    src_cs = src_coords[0].coord_system
#    sample_grid_x, sample_grid_y = i_regrid._sample_grid(src_cs,
#                                                         dst_coords[0],
#                                                         dst_coords[1])

#    result_cube = iris.cube.Cube(fullcube_data)
#    result_cube.metadata = source_cube.metadata
#
#    for coord in dst_coords:
#        result_cube.add_aux_coord(coord, grid_cube.coord_dims(coord))
#
#    return result_cube

    # Return result_cube as a new cube based on the source.
    # TODO: please tidy this interface !!!
    # NOTE: the 'regrid' parts are unused, as we already checked that the
    # source had no horizontal coordinate factories.
    return i_regrid._create_cube(
        fullcube_data,
        src=source_cube,
        x_dim=src_dims_xy[0],
        y_dim=src_dims_xy[1],
        src_x_coord=src_coords[0],
        src_y_coord=src_coords[1],
        grid_x_coord=dst_coords[0],
        grid_y_coord=dst_coords[1],
        sample_grid_x=None,
        sample_grid_y=None,
        regrid_callback=None)
