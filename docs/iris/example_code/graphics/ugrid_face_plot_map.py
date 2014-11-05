# (C) British Crown Copyright 2014, Met Office
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
An example of plotting unstructured grid data over a map.

"""

from __future__ import (absolute_import, division, print_function)


import iris.tests as tests
import matplotlib.pyplot as plt
plt.switch_backend('tkagg')

import cartopy.crs as ccrs
from matplotlib.tri import Triangulation
import unittest

# Import pyugrid if installed, else fail quietly + disable all the tests.
try:
    import pyugrid
    # Check it *is* the real module, and not an iris.proxy FakeModule.
    pyugrid.ugrid
except (ImportError, AttributeError):
    pyugrid = None
skip_pyugrid = unittest.skipIf(
    condition=pyugrid is None,
    reason='Requires pyugrid, which is not available.')

import iris.experimental.ugrid


def ugrid_cube_triangulation(ucube):
    """Return a matplotlib triangulation object from a ugrid cube."""
    # For now, only support ugrid formatted, face-located cubes
    mesh = ucube.mesh
    # get coordinate values for nodes.
    x = mesh.nodes[:, 0]
    y = mesh.nodes[:, 1]
    return Triangulation(x, y, mesh.faces)  # N.B. could also take face-mask from data here ?


def plot_ucube_faces(ucube, **kwargs):
    """Make a simple plot that shows nodes, edges and faces."""
    assert ucube.attributes['location'] == 'face'
    tri = ugrid_cube_triangulation(ucube)
    plt.tripcolor(tri, ucube.data, **kwargs)
    plt.triplot(tri, '-', color='black', **kwargs)
    plt.triplot(tri, 'o', color='red', **kwargs)


def ugrid_plot_example():
    data_path = ("NetCDF", "ugrid", )
    file21 = "21_triangle_example.nc"
    long_name = "eastward_sea_water_velocity"
    path = tests.get_data_path(data_path + (file21, ))
    ucube = iris.experimental.ugrid.ugrid(path, long_name)
    # Hack the points to rebase near the UK (for nicer maps).
    ucube.mesh.nodes[:, 1] *= 0.4
    ucube.mesh.nodes[:, 1] += 52
    ucube.mesh.nodes[:, 0] *= 0.4
    ucube.mesh.nodes[:, 0] += -5.5

    plt.figure(figsize=(12,8))
    
#    ax = plt.axes(projection=ccrs.NorthPolarStereo())
    ax = plt.subplot(121, projection=ccrs.Orthographic())
    ax.coastlines()
    plot_ucube_faces(ucube, transform=ccrs.PlateCarree())
    ax.set_extent((-8, 2, 48, 65), crs=ccrs.PlateCarree())

    ax = plt.subplot(122, projection=ccrs.RotatedPole(75, -120))
    ax.coastlines()
    plot_ucube_faces(ucube, transform=ccrs.PlateCarree())
    ax.set_extent((-8, 2, 48, 65), crs=ccrs.PlateCarree())

    plt.show()


if __name__ == "__main__":
    ugrid_plot_example()
