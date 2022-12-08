# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""
A temporary proof-of-concept test workflow

"""
import numpy as np
import xarray as xr

import iris
from iris.experimental.xarray_bridge import cubes_from_xarray, cubes_to_xarray
import iris.tests as itsts


def example_from_xr():
    iris.FUTURE.datum_support = True
    filepath = itsts.get_data_path(
        ["NetCDF", "stereographic", "toa_brightness_temperature.nc"]
    )
    xrds = xr.open_dataset(filepath, chunks="auto")
    print("\nOriginal Xarray dataset:\n", xrds)
    cubes = cubes_from_xarray(xrds)
    print("\nxrds['time']:\n", xrds["time"])
    print("\n\n")
    print("============ CONVERT xr.Dataset TO cubes ... =========\n")
    print("Cubes:")
    print(cubes)
    cube = cubes[0]
    print("\nCube:")
    print(cube)
    data = cube.core_data()
    print("\ncube.core_data():")
    print(data)
    # match = data is xrds['data'].data
    # print('\ncube.core_data() is xrds["data"].data:')
    # print(match)
    co_auxlons = cube.coord("longitude")
    print('\ncube.coord("longitude"):')
    print(co_auxlons)
    points = co_auxlons.core_points()
    print('\ncube.coord("longitude").core_points():')
    print(points)
    print('\ncube.coord("longitude").points:')
    print(points.compute())

    print("\n")
    print("============ CONVERT cubes TO xr.Dataset ... =========")
    print("")
    xrds2 = cubes_to_xarray(cubes)
    print("\nxrds2:\n", xrds2)
    print("\ntime:\n", xrds2["time"])

    print("\n")
    print("============ Array identity checks ... =========")
    print(
        "xrds2['data'].data   is   cube.core_data() : ",
        bool(xrds2["data"].data is cube.core_data()),
    )
    print(
        "xrds2['lon'].data   is   cube.coord('longitude').core_points() : ",
        bool(xrds2["lon"].data is cube.coord("longitude").core_points()),
    )
    print(
        "xrds2['x'].data   is   cube.coord('projection_x_coordinate').core_points() : ",
        bool(
            xrds2["x"].data
            is cube.coord("projection_x_coordinate").core_points()
        ),
    )
    print(
        "np.all(xrds2['x'].data == cube.coord('projection_x_coordinate').points) : ",
        bool(
            np.all(
                xrds2["x"].data == cube.coord("projection_x_coordinate").points
            )
        ),
    )


if __name__ == "__main__":
    example_from_xr()
