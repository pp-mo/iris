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
    Create an ESMPy ESMF.Field on given coordinates.

    Create a ESMF.Grid from the coordinates, defining corners and centre
    positions as lats+lons.
    Add a grid mask if provided.
    Create and return a Field mapped on this Grid, setting data if provided.

    Args:

    * x_coord, y_coord (:class:`iris.coords.Coord`):
        One-dimensional coordinates of shape (nx,) and (ny,).
        Their contiguous bounds define an ESMF.Grid of shape (nx, ny).

    Kwargs:

    * data (:class:`numpy.ndarray`, shape (nx,ny)):
        Set the Field data content.
    * mask (:class:`numpy.ndarray`, boolean, shape (nx,ny)):
        Add a mask item to the grid, assigning it 0/1 where mask=False/True.

    """
    # Create a Grid object describing the coordinate cells.
    dims = [len(coord.points) for coord in (x_coord, y_coord)]
    dims = np.array(dims, dtype=np.int32)  # specific type required by ESMF.
    grid = ESMF.Grid(dims)

    # Get all cell corner coordinates as true-lat-lons
    x_bounds, y_bounds = np.meshgrid(x_coord.contiguous_bounds(),
                                     y_coord.contiguous_bounds())
    grid_crs = x_coord.coord_system.as_cartopy_crs()
    lon_bounds, lat_bounds = _convert_latlons(grid_crs, x_bounds, y_bounds)

    # Add grid 'coord' element for corners, and fill with corner values.
    grid.add_coords(staggerlocs=[ESMF.StaggerLoc.CORNER])
    grid_corners_x = grid.get_coords(0, ESMF.StaggerLoc.CORNER)
    grid_corners_x[:] = lon_bounds.T
    grid_corners_y = grid.get_coords(1, ESMF.StaggerLoc.CORNER)
    grid_corners_y[:] = lat_bounds.T

    # calculate the cell centre-points
    # NOTE: we don't care about Iris' idea of where the points 'really' are
    # *but* ESMF requires the data in the CENTER for conservative regrid,
    # according to the documentation :
    #  - http://www.earthsystemmodeling.org/
    #        esmf_releases/public/last/ESMF_refdoc.pdf
    #  - section  22.2.3 : ESMF_REGRIDMETHOD
    #
    # We are currently determining cell centres in native coords, then
    # converting these into true-lat-lons.
    # It is confirmed by experiment that moving these centre location *does*
    # changes the regrid results.
    # TODO: work out why this is needed, and whether these centres are 'right'.

    # Average cell corners in native coordinates, then translate to lats+lons
    # (more costly, but presumably 'more correct' than averaging lats+lons).
    x_centres = x_coord.contiguous_bounds()
    x_centres = 0.5 * (x_centres[:-1] + x_centres[1:])
    y_centres = y_coord.contiguous_bounds()
    y_centres = 0.5 * (y_centres[:-1] + y_centres[1:])
    x_points, y_points = np.meshgrid(x_centres, y_centres)
    lon_points, lat_points = _convert_latlons(grid_crs, x_points, y_points)

    # Add grid 'coord' element for centres + fill with centre-points values.
    grid.add_coords(staggerlocs=[ESMF.StaggerLoc.CENTER])
    grid_centers_x = grid.get_coords(0, ESMF.StaggerLoc.CENTER)
    grid_centers_x[:] = lon_points.T
    grid_centers_y = grid.get_coords(1, ESMF.StaggerLoc.CENTER)
    grid_centers_y[:] = lat_points.T

    # Add a mask item, if requested
    if mask is not None:
        grid.add_item(ESMF.GridItem.MASK,
                      [ESMF.StaggerLoc.CENTER])
        grid_mask = grid.get_item(ESMF.GridItem.MASK)
        grid_mask[:] = np.where(mask, 1, 0)

    # create a Field based on this grid
    field = ESMF.Field(grid, ref_name)

    # assign data content, if provided
    if data is not None:
        field.data[:] = data

    return field


def _make_esmpy_meshtype_field(x_coord, y_coord, ref_name='field',
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
#        # set up a simple mesh
#        num_node = 16
#        num_elem = 9
#        nodeId = np.array([1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16])
#        nodeCoord = np.array([0.0,0.0, 1.5,0.0, 2.5,0.0, 4.0,0.0,
#                              0.0,1.5, 1.5,1.5, 2.5,1.5, 4.0,1.5,
#                              0.0,2.5, 1.5,2.5, 2.5,2.5, 4.0,2.5,
#                              0.0,4.0, 1.5,4.0, 2.5,4.0, 4.0,4.0])
#        nodeOwner = np.zeros(num_node, dtype=np.int32)
#        elemId = np.array([1,2,3,4,5,6,7,8,9], dtype=np.int32)
#        elemType = np.ones(num_elem, dtype=np.int32)
#        elemType*=ESMF.MeshElemType.QUAD
#        elemConn = np.array([0,1,5,4,
#                              1,2,6,5,
#                              2,3,7,6,
#                              4,5,9,8,
#                              5,6,10,9,
#                              6,7,11,10,
#                              8,9,13,12,
#                              9,10,14,13,
#                              10,11,15,14], dtype=np.int32)
#        elemMask = np.array([0,0,0,0,1,0,0,0,0], dtype=np.int32)
#        elemArea = np.array([5,5,5,5,5,5,5,5,5], dtype=np.float64)
#        
#        mesh = ESMF.Mesh(2,2)
#        
#        mesh.add_nodes(num_node, nodeId, nodeCoord, nodeOwner)
#        
#        mesh.add_elements(num_elem, elemId, elemType, elemConn, elemMask, elemArea)

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

    n_extras = 0
    if n_extras:
        #
        # Invent extra mesh nodes + elements, that will be ok, to test the debug mechanism
        #
        lon_extras = np.arange(n_extras).reshape(n_extras,1)*10.0 + \
            [[21.1, 21.5, 21.5, 21.1]]
        lat_extras = np.arange(n_extras).reshape(n_extras,1)*15.0 + \
            [[51.1, 51.1, 51.5, 51.5]]
        extra_coords = np.concatenate((lon_extras[..., None],
                                       lat_extras[..., None]),
                                      axis=-1).flat[:]
        combined_node_coords = np.concatenate((extra_coords, combined_node_coords))
        extra_node_ids = np.array(np.arange(n_extras*4) + 5000000,
                                  np.int32)
        node_ids = np.concatenate((extra_node_ids, node_ids))
        n_nodes += n_extras*4
        node_owners = np.zeros(n_nodes)

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
    if n_extras:
        n_elems += n_extras
        elem_ids = np.arange(n_elems, dtype=np.int32)
        elem_types = np.ones(n_elems, dtype=np.int32) * ESMF.MeshElemType.QUAD
        elem_connects = np.concatenate((np.arange(n_extras*4, dtype=np.int32),
                                        elem_connects.flat[:] + n_extras*4))
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
        if n_extras:
            data = np.concatenate((np.zeros(n_extras), data.flat[:]))
        field.data[:] = data.reshape(n_cells)[i_ok]

    return field


def regrid_conservative_via_esmpy(source_cube, grid_cube):
    """
    Perform a conservative regridding with ESMPy.

    Regrids the data of a source cube onto a new grid defined by a destination
    cube.

    Args:

    * source_cube (:class:`iris.cube.Cube`):
        Source data.  Must have two identifiable horizontal dimension
        coordinates.
    * grid_cube (:class:`iris.cube.Cube`):
        Define the target horizontal grid:  Only the horizontal dimension
        coordinates are actually used.

    Returns:
        A new cube derived from source_cube, regridded onto the specified
        horizontal grid.

    Any additional coordinates which map onto the horizontal dimensions are
    removed, while all other metadata is retained.
    If there are coordinate factories with 2d horizontal reference surfaces,
    the reference surfaces are also regridded, using ordinary bilinear
    interpolation.

    .. note::

        Both source and destination cubes must have two dimension coordinates
        identified with axes 'X' and 'Y' which share a coord_system with a
        Cartopy CRS.
        The grids are defined by :meth:`iris.coords.Coord.contiguous_bounds` of
        these.

    .. note::

        Initialises the ESMF Manager, if it was not already called.
        This implements default Manager operations (e.g. logging).

        To alter this, make a prior call to ESMF.Manager().

    """

    # Get source + target XY coordinate pairs and check they are suitable.
#    src_coords = i_regrid._get_xy_dim_coords(source_cube)
#    dst_coords = i_regrid._get_xy_dim_coords(grid_cube)
    src_coords = source_cube.coord(axis='x'), source_cube.coord(axis='y')
    dst_coords = grid_cube.coord(axis='x'), grid_cube.coord(axis='y')
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

    if not all(_valid_units(coord) for coord in src_coords + dst_coords):
        raise ValueError("Unsupported units: must be 'degrees' or 'm'.")

    # Initialise the ESMF manager in case it was not already done.
    ESMF.Manager(logkind=ESMF.LogKind.SINGLE)

    # Create a data array for the output cube.
#    src_dims_xy = [source_cube.coord_dims(coord)[0] for coord in src_coords]
#    # Size matches source, except for X+Y dimensions
#    dst_shape = np.array(source_cube.shape)
#    dst_shape[src_dims_xy] = [coord.shape[0] for coord in dst_coords]
    dst_shape = grid_cube.shape

    # NOTE: result_cube array is masked -- fix this afterward if all unmasked
    fullcube_data = np.ma.zeros(dst_shape)

    if 1:
#    # Iterate 2d slices over all possible indices of the 'other' dimensions
#    all_other_dims = filter(lambda i_dim: i_dim not in src_dims_xy,
#                            xrange(source_cube.ndim))
#    all_combinations_of_other_inds = np.ndindex(*dst_shape[all_other_dims])
#    for other_indices in all_combinations_of_other_inds:
#        # Construct a tuple of slices to address the 2d xy field
#        slice_indices_array = np.array([slice(None)] * source_cube.ndim)
#        slice_indices_array[all_other_dims] = other_indices
#        slice_indices_tuple = tuple(slice_indices_array)
#
#        # Get the source data, reformed into the right dimension order, (x,y).
#        src_data_2d = source_cube.data[slice_indices_tuple]
#        if (src_dims_xy[0] > src_dims_xy[1]):
#            src_data_2d = src_data_2d.transpose()
#
        assert source_cube.ndim == 2
        # NB must transpose data, as we have (y, x) dims order
        #    (well usually, *not checked here*)
        # .. but ESMF uses (x, y)
        src_data_2d = source_cube.data.copy()
        # Work out whether we have missing data to define a source grid mask.
        if np.ma.is_masked(src_data_2d):
            srcdata_mask = np.ma.getmask(src_data_2d)
        else:
            srcdata_mask = None

        # Construct ESMF Field objects on source and destination grids.
#        src_field = _make_esmpy_field(src_coords[0], src_coords[1],
#                                      data=src_data_2d, mask=srcdata_mask)

        src_field = _make_esmpy_meshtype_field(src_coords[0], src_coords[1],
                                         data=src_data_2d, mask=srcdata_mask)

#        dst_field = _make_esmpy_field(dst_coords[0], dst_coords[1])
        dst_field = _make_esmpy_meshtype_field(dst_coords[0], dst_coords[1])
#                                               data=grid_cube.data.transpose())

        # Make Field for destination coverage fraction (for missing data calc).
#        coverage_field = ESMF.Field(dst_field.grid, 'validmask_dst')
        coverage_field = _make_esmpy_meshtype_field(dst_coords[0],
                                                    dst_coords[1])

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

#
# NOTE: this should really transpose to DESTINATION ORDER
#  - in any case, that is unclear now target-dims are also 2d (!)
#
#        # Transpose ESMF result_cube dims (X,Y) back to the order of the source
#        if (src_dims_xy[0] > src_dims_xy[1]):
#            data = data.transpose()

#        # Paste regridded slice back into parent array
#        fullcube_data[slice_indices_tuple] = data
        fullcube_data = data

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

    result_cube = iris.cube.Cube(fullcube_data)
    result_cube.metadata = source_cube.metadata

    for coord in dst_coords:
        result_cube.add_aux_coord(coord, grid_cube.coord_dims(coord))

    return result_cube

#    # Return result_cube as a new cube based on the source.
#    # TODO: please tidy this interface !!!
#    return i_regrid._create_cube(
#        fullcube_data,
#        src=source_cube,
#        x_dim=src_dims_xy[0],
#        y_dim=src_dims_xy[1],
#        src_x_coord=src_coords[0],
#        src_y_coord=src_coords[1],
#        grid_x_coord=dst_coords[0],
#        grid_y_coord=dst_coords[1],
#        sample_grid_x=sample_grid_x,
#        sample_grid_y=sample_grid_y,
#        regrid_callback=i_regrid._regrid_bilinear_array)
