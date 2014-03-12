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
import iris.unit
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


_unit_degrees = iris.unit.Unit('degrees')


def _make_esmpy_field(x_coord, y_coord, ref_name='field',
                     data=None, mask=None):
    """
    Create an ESMPy ESMF.Field on given coordinates, based on a ESMF.Mesh.

    Create a ESMF.Mesh from the coordinates, defining corners from the
    coordinate values.  Return an ESMF.Field based on this, setting the point
    data if provided.  The separate mask argument, if provided, specifies cells
    to be omitted from the underlying Mesh.

    Args:

    * x_coord, y_coord (:class:`iris.coords.Coord`):
        X and Y coordinates, either one- or two-dimensional (both the same).
        The resulting ESMF.Field is based on an ESMF.Mesh representing 2d
        bounds derived from these coordinates.

    Kwargs:

    * ref_name (string):
        A user id-name for the field.
    * data (float array-like):
        Set the Field data content.
    * mask (boolean array-like):
        Specifies cells to be omitted from the underlying Mesh.

    .. note::

        Each set of four cell bound points must conform to ESMF validity
        requirements:  The points must all be distinct, and the values trace a
        convex, anti-clockwise path describing a finite area (i.e. not flat).
        The 'mask' can be used to omit cells that will otherwise cause errors.

    .. note::

        Although ESMF supports arbitrary coordinate types, here we require that
        X and Y are longitude and latitude coordinates.

    """
    # Get all cell corner coordinates as 2D arrays
    if x_coord.ndim == 2:
        # 2D source coordinates: define 2d sets contiguously
        x_bounds = x_coord.bounds
        y_bounds = y_coord.bounds
    else:
        # 1D source coordinates: define 2d sets contiguously
        x_bounds_contiguous, y_bounds_contiguous = np.meshgrid(
            x_coord.contiguous_bounds(),
            y_coord.contiguous_bounds())

        # Expand these into general 4-point bounds (i.e. they now just "happen"
        # to be contiguous!): points 0,1,2,3 anticlockwise around the cell.
        def _make_full_bounds_array(bounds_contiguous):
            bounds_full_4point = np.empty((bounds_contiguous.shape[0] - 1,
                                           bounds_contiguous.shape[1] - 1,
                                           4))
            bounds_full_4point[..., 0] = bounds_contiguous[:-1, :-1]
            bounds_full_4point[..., 1] = bounds_contiguous[:-1, 1:]
            bounds_full_4point[..., 2] = bounds_contiguous[1:, 1:]
            bounds_full_4point[..., 3] = bounds_contiguous[1:, :-1]
            return bounds_full_4point

        x_bounds = _make_full_bounds_array(x_bounds_contiguous)
        y_bounds = _make_full_bounds_array(y_bounds_contiguous)


    ny, nx = x_bounds.shape[:-1]
    n_cells = nx * ny

    # Convert the coordinate values to degrees (as coord_systems need this)
    x_bounds = x_coord.units.convert(x_bounds, _unit_degrees)
    y_bounds = x_coord.units.convert(y_bounds, _unit_degrees)

    # Transform these into "true" longitudes and latitudes.
    grid_crs = x_coord.coord_system.as_cartopy_crs()
    x_bounds, y_bounds = _convert_latlons(grid_crs,
                                          x_bounds.flat[:], y_bounds.flat[:])

    # Reform so the values are indexed simply by [cell_index, bounds_index].
    x_bounds = x_bounds.reshape((n_cells, 4))
    y_bounds = y_bounds.reshape((n_cells, 4))

    # Fix the longitudes to avoid any 180-degree crossings within each cell.
    angle_calcs.fix_longitude_bounds(x_bounds)

#    do_prune_to_valid = True
    do_prune_to_valid = False

#    # Calculate which cells are 'valid' (in ESMF terms, at least).
#    if do_prune_to_valid:
#        i_ok = angle_calcs.valid_bounds_shapes(x_bounds, y_bounds)
#        if mask is not None:
#            i_ok &= ~mask
#    else:
#        i_ok = ~mask

    i_ok = np.ones((n_cells), dtype=bool)
    if mask is not None:
        i_ok &= ~mask.flat[:]

#    if do_prune_to_valid:
#        assert np.all(i_ok)

    # Convert to a valid-indices array (for now -- for older code approach).
    i_ok = np.array(np.where(i_ok)[0])

    n_validpoints = i_ok.size

    x_bounds = x_bounds[i_ok]
    y_bounds = y_bounds[i_ok]

    if not np.all(angle_calcs.valid_bounds_shapes(x_bounds, y_bounds)):
        try:
            angle_calcs.fix_bounds_with_longitude_flips(x_bounds, y_bounds)
        except ValueError as e:
            i_bads = np.where(~angle_calcs.valid_bounds_shapes(x_bounds,
                                                               y_bounds))[0]
            print 'Bad cells found! ({} of)'.format(len(i_bads))
            for i_bad in i_bads:
                print '\n#{}:\n'.format(i_bad)
                msg = '{} = np.array([{:10.5g}, {:10.5g}, {:10.5g}, {:10.5g}])'
                print msg.format('xx', *x_bounds[i_bad])
                print msg.format('yy', *y_bounds[i_bad])
                for x, y in zip(x_bounds[i_bad], y_bounds[i_bad]):
                    print '    {:10.5g}, {:10.5g}'.format(x, y)
#            raise ValueError("Bad cells in grid.")
            # plt.plot(xx, yy, '-'); [plt.plot(x, y, 'x', markersize=20, color=c) for x, y, c in zip(xx, yy, ['black', 'red', 'blue', 'green'])]; plt.show()

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
    n_nodes = x_bounds.size
    node_ids = np.arange(n_nodes, dtype=np.int32)
    # Create a map of all-zeros for the 'node owners' field
    node_owners = np.zeros(n_nodes)
    # Concatenate all the bounds position coords
    combined_node_coords = np.concatenate((x_bounds[..., None],
                                           y_bounds[..., None]),
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

    mesh.add_elements(elementCount=n_elems,
                      elementIds=elem_ids.flat[:],
                      elementTypes=elem_types.flat[:],
                      elementConn=elem_connects.flat[:],
                      elementMask=None)

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

    # Work out the dimensions occupied by the horizontal coordinates
    def xy_dims(cube, xy_coords):
        if xy_coords[0].ndim == 1:
            # 1d X and Y occupy two separate source dimensions
            xy_dims = [cube.coord_dims(coord)[0]
                           for coord in xy_coords]
        else:
            # 2d X and Y *share* two source dimensions.
            xy_dims = cube.coord_dims(xy_coords[0])
            # NB we need these in x, y order (opposite to normal)
            xy_dims = (xy_dims[1], xy_dims[0])
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

    # NOTE: result_cube array is masked -- fix this afterward if all unmasked
    fullcube_data = np.ma.zeros(dst_shape)

    # Iterate 2d slices over all possible indices of the 'other' dimensions
    all_other_dims = filter(lambda i_dim: i_dim not in src_dims_xy,
                            xrange(source_cube.ndim))
    all_combinations_of_other_inds = np.ndindex(*dst_shape[all_other_dims])
    for other_indices in all_combinations_of_other_inds:
        # Construct a tuple of slices to address the 2d xy field
        slice_indices_array = np.array([slice(None)] * source_cube.ndim)
        slice_indices_array[all_other_dims] = other_indices
        slice_indices_tuple = tuple(slice_indices_array)

        # Get the source data, as a 2d array.
        src_data_2d = source_cube.data[slice_indices_tuple]

        # Reform to the 'standard' dimension order = y,x.
        if src_dims_xy[0] < src_dims_xy[1]:
            src_data_2d = src_data_2d.transpose()

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

        # Reconstruct correct 2d form.
        data = data.reshape([grid_cube.shape[i_dim]
                             for i_dim in [dst_dims_xy[1], dst_dims_xy[0]]])

        # Reform into dimension order required by result cube.
        if src_dims_xy[0] < src_dims_xy[1]:
            data = data.transpose()

        #Paste regridded slice back into parent array
        fullcube_data[slice_indices_tuple] = data

    # Remove the data mask if completely unused.
    if not np.ma.is_masked(fullcube_data):
        fullcube_data = np.array(fullcube_data)

    # Return result_cube as a new cube based on the source.
    # TODO: please tidy this interface !!!
    # NOTE: the 'regrid' parts are unused, as we already checked that the
    # source had no horizontal coordinate factories.
    return i_regrid._create_cube_xy_1d_or_2d(
        data=fullcube_data,
        src=source_cube,
        grid=grid_cube,
        src_x_coord=src_coords[0],
        src_y_coord=src_coords[1],
        src_xy_dims=src_dims_xy,
        grid_x_coord=dst_coords[0],
        grid_y_coord=dst_coords[1],
        grid_xy_dims=dst_dims_xy)
