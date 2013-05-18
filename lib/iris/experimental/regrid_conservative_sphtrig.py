# (C) British Crown Copyright 2013 Met Office
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
Support for conservative regridding via prototype spherical_geometry.

A clone of the original 'regrid_conservative' module, with inner calculations
re-implemented.

"""

import numpy as np

#import ESMF
import iris.experimental.spherical_geometry as sph

import cartopy.crs as ccrs
import iris
import iris.experimental.regrid as i_regrid


def _get_coord_crs(coord):
    """ Get the Cartopy crs relevant to a coordinate (or None). """
    cs = coord.coord_system
    if cs is None:
        return None
    return cs.as_cartopy_crs()


_crs_truelatlon = ccrs.Geodetic()
""" A static Cartopy Geodetic() instance for transforming to true-lat-lons. """


def _convert_latlons(crs, x_array, y_array):
    """
    Convert x+y coords in a given crs to (x,y) values in true-lat-lons.

    ..note:
        Uses a plain Cartopy Geodetic to convert to true-lat-lons.  This makes
        no allowance for a non-spherical earth.  But then, neither does ESMF.

    """
    ll_values = _crs_truelatlon.transform_points(crs, x_array, y_array)
    return ll_values[..., 0], ll_values[..., 1]


def _make_SphPolygon_array_from_coords(x_coord, y_coord):
    """
    Make an array of sph.SphAcwConvexPolygon objects representing XY cells.

    Args:

    * x_coord, y_coord (:class:`iris.coords.Coord`):
        One-dimensional coordinates of shape (nx,) and (ny,).
        Their contiguous bounds define an ESMF.Grid of shape (nx, ny).

    """
    # Create a Grid object describing the coordinate cells.
    dims = [len(coord.points) for coord in (x_coord, y_coord)]

    # Get all cell corner coordinates as true-lat-lons
    x_bounds, y_bounds = np.meshgrid(x_coord.contiguous_bounds(),
                                     y_coord.contiguous_bounds())
    grid_crs = _get_coord_crs(x_coord)
    lon_bounds, lat_bounds = _convert_latlons(grid_crs, x_bounds, y_bounds)

    # Create sph Polygons for each one.
    cells = np.empty(dims, dtype=object)
    for ix in xrange(dims[0]):
        for iy in xrange(dims[1]):
            points = [(lat_bounds[ix, iy], lon_bounds[ix, iy]),
                      (lat_bounds[ix+1, iy], lon_bounds[ix+1, iy]),
                      (lat_bounds[ix+1, iy+1], lon_bounds[ix+1, iy+1]),
                      (lat_bounds[ix, iy+1], lon_bounds[ix, iy+1])]
            cells[ix, iy] = sph.SphAcwConvexPolygon(points, in_degrees=True)

    return cells


def _regrid_inner(src_data_2d, src_coords, dst_coords):
    """
    "Perform area-conservative regridding.

    Args:
    * src_data_2d (np.array, optionally masked):
        source data
    * src_coords, dst_coords (pairs of Coord):
        grid coords.  Only bounds will be used (may be inferred).
    """
    src_polygons = _make_SphPolygon_array_from_coords(*src_coords)
    dst_polygons = _make_SphPolygon_array_from_coords(*dst_coords)

    # Tolerancing for overlap with masked source, or outside source bounds
    coverage_eps = 1.0e-6
    coverage_tolerance_threshold = 1.0 - coverage_eps

    src_nx, src_ny = [len(coord.points) for coord in src_coords]
    dst_nx, dst_ny = [len(coord.points) for coord in dst_coords]
    dst_data = np.ma.empty((dst_nx, dst_ny), dtype=np.double)
    ones_where_src_masked = np.ma.getmaskarray(src_data_2d).astype(float)
    ones_where_src_masked = ones_where_src_masked.flatten()
    for dst_ix in range(dst_nx):
        for dst_iy in range(dst_ny):
            dst_polygon = dst_polygons[dst_ix, dst_iy]
            dst_area = dst_polygon.area()
            per_src_overlaps = [dst_polygon.intersection_with_polygon(src)
                                for src in src_polygons.flat]
            per_src_overlaps = [poly.area() if poly is not None else 0.0
                                for poly in per_src_overlaps]
            overlaps_sum = sum(per_src_overlaps)
            if overlaps_sum < dst_area * coverage_tolerance_threshold:
                # Masked as not entirely within source bounds.
                dst_value = np.ma.masked
            else:
                per_src_overlaps = np.array(per_src_overlaps) / overlaps_sum
                masked_src_fraction = np.sum(per_src_overlaps
                                             * ones_where_src_masked)
                if masked_src_fraction > coverage_eps:
                    # Masked as it touches some masked source cells.
                    dst_value = np.ma.masked
                else:
                    # Form weighted sum
                    per_src_overlaps = per_src_overlaps.reshape(
                        (src_nx, src_ny))
                    dst_value = np.sum(src_data_2d * per_src_overlaps)
            dst_data[dst_ix, dst_iy] = dst_value
    return dst_data


def regrid_conservative_via_sph(source_cube, grid_cube_or_coords):
    """
    Perform a conservative regridding with experimental spherical_geometry,
    comparable to ESMPy-based function in regrid_conservative.

    Regrids the data of a source cube onto a new grid defined by a destination
    cube or coordinates.

    Args:

    * source_cube (:class:`iris.cube.Cube`):
        Source data.  Must have two identifiable horizontal dimension
        coordinates.
    * grid_cube_or_coords :
        Either a :class:`iris.cube.Cube`, or a pair of
        :class:`iris.coords.Coord`, defining the target horizontal grid.
        If a cube, *only* the horizontal dimension coordinates are used.

    Returns:
        A new cube derived from source_cube, regridded onto the specified
        horizontal grid.

    Any additional coordinates mapped onto horizontal spatial axes are removed,
    while all other metadata is retained.

    Any factory-derived auxiliary coordinates are regridded with linear
    interpolation.

    .. note::
        Both source and destination cubes must have two dimension coordinates
        identified with axes 'x' and 'y' which share a known coord_system.
        The grids are defined by :meth:`iris.coords.Coord.contiguous_bounds` of
        these.

    """
    # Process parameters to get input+output horizontal coordinates.
    src_coords = i_regrid._get_xy_dim_coords(source_cube)
    if isinstance(grid_cube_or_coords, iris.cube.Cube):
        dst_coords = i_regrid._get_xy_dim_coords(grid_cube_or_coords)
    else:
        dst_coords = grid_cube_or_coords

    # Check source+target coordinates are suitable.
    # NOTE: '_get_xy_dim_coords' ensures the coords exist; are unique; and have
    # same coord_system.  We also need them to have a _valid_ coord_system.
    if _get_coord_crs(src_coords[0]) is None:
        raise ValueError('Source X+Y coordinates have no coord_system.')
    if _get_coord_crs(dst_coords[0]) is None:
        raise ValueError('Destination X+Y coordinates have no coord_system.')

    # Create a data array for the output cube.
    src_dims_xy = [source_cube.coord_dims(coord)[0] for coord in src_coords]
    # Size matches source, except for X+Y dimensions
    dst_shape = np.array(source_cube.shape)
    dst_shape[src_dims_xy] = [coord.shape[0] for coord in dst_coords]
    # NOTE: result array is masked -- fix this afterward if all unmasked
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

        # Get the source data, reformed into the right dimension order, (x,y).
        src_data_2d = source_cube.data[slice_indices_tuple]
        if (src_dims_xy[0] > src_dims_xy[1]):
            src_data_2d = src_data_2d.transpose()

        data = _regrid_inner(src_data_2d, src_coords, dst_coords)

        # Transpose ESMF result dims (X,Y) back to the order of the source
        if (src_dims_xy[0] > src_dims_xy[1]):
            data = data.transpose()

        # Paste regridded slice back into parent array
        fullcube_data[slice_indices_tuple] = data

    # Remove the data mask if completely unused.
    if not np.ma.is_masked(fullcube_data):
        fullcube_data = np.array(fullcube_data)

    # Generate a full 2d sample grid, as required for regridding orography
    # NOTE: as seen in "regrid_bilinear_rectilinear_src_and_grid"
    # TODO: can this not also be wound into the _create_cube method ?
    src_cs = src_coords[0].coord_system
    sample_grid_x, sample_grid_y = i_regrid._sample_grid(src_cs,
                                                         dst_coords[0],
                                                         dst_coords[1])

    # Return result as a new cube based on the source.
    # TODO: please tidy this interface !!!
    return i_regrid._create_cube(
        fullcube_data,
        src=source_cube,
        x_dim=src_dims_xy[0],
        y_dim=src_dims_xy[1],
        src_x_coord=src_coords[0],
        src_y_coord=src_coords[1],
        grid_x_coord=dst_coords[0],
        grid_y_coord=dst_coords[1],
        sample_grid_x=sample_grid_x,
        sample_grid_y=sample_grid_y,
        regrid_callback=i_regrid._regrid_bilinear_array)
