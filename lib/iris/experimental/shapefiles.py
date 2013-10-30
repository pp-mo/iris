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
"""Experimental module for exporting cubes to shapefiles."""

import itertools
import numpy as np
import os.path
import shapefile

import cartopy.crs as ccrs
import iris


def export_shapefiles(cube, output_name):
    """
    Output a 2D cube as points in a shapefile.

    Args:

    * cube (:class:`iris.cube.Cube`):
    The cube to be exported.  Must be 2D with dimension coordinates on X and Y
    axes, in a specified, common coordinate system.

    * output_name (string):
    A filepath basis to write to.  The actual filenames will be based on this,
    with various extensions as appropriate, as provided by
    :meth:`shapefile.Writer.save`.  A standard projection file is also
    generated.

    .. note::

        Shapefile projections are not supported.  Instead, all locations are
        converted to longitude and latitude points, and a .prj file is
        generated which specifies the coordinate system as lat-lon on WGS84.

    """
    if cube.ndim != 2:
        raise ValueError("The cube must be two dimensional.")

    coord_x = cube.coord(axis='X', dim_coords=True)
    coord_y = cube.coord(axis='Y', dim_coords=True)

    if coord_x is None or coord_y is None or \
       coord_x.coord_system != coord_y.coord_system or \
       coord_x.coord_system is None:
        raise ValueError('The X and Y coordinates must both have the same, '
                         'specifed CoordSystem.')

    crs_data = coord_x.coord_system.as_cartopy_crs()
    crs_latlon = ccrs.Geodetic()
    x_array, y_array = np.meshgrid(coord_x.points, coord_y.points)
    ll_values = crs_latlon.transform_points(crs_data, x_array, y_array)
    lons_array = ll_values[..., 0]
    lats_array = ll_values[..., 1]
    data = cube.data
    if cube.coord_dims(coord_x)[0] < cube.coord_dims(coord_y)[0]:
        data = data.T
    points_data = itertools.izip(lons_array.flat, lats_array.flat, data.flat)

    writer = shapefile.Writer(shapeType=shapefile.POINT)
    writer.field('data_value')
    for x, y, value in points_data:
        writer.point(x, y)
        writer.record(value)
    writer.save(output_name)

    # Also create a project file.
    # For this we must mimic the path-management of shapefile.Writer.save
    # so the method is cribbed from there.
    standard_latlon_projection_string = (
        'GEOGCS["WGS 84",'
        'DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],'
        'PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]')
    target = output_name
    target = os.path.splitext(target)[0] + '.prj'
    with open(target, 'w') as proj_file:
        proj_file.write(standard_latlon_projection_string)
