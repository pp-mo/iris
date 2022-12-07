# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""
An abstract representation of Netcdf structured data, according to the
"Common Data Model" : https://docs.unidata.ucar.edu/netcdf-java/5.3/userguide/common_data_model_overview.html

TODO:
  * add consistency checking
  * add "direct" netcdf interfacing, i.e. to_nc4/from_nc4

"""
import iris
from iris.cube import CubeList
import iris.fileformats.netcdf as ifn

from .dataset_like import Nc4DatasetLike
from .xarray import from_xarray, to_xarray

#
# The primary conversion interfaces
#


def cubes_from_xarray(xrds: "xarray.Dataset", **xr_load_kwargs):  # noqa
    ncdata = from_xarray(xrds, **xr_load_kwargs)
    dslike = Nc4DatasetLike(ncdata)
    cubes = CubeList(ifn.load_cubes(dslike))
    return cubes


def cubes_to_xarray(cubes, iris_save_kwargs=None, xr_save_kwargs=None):
    iris_save_kwargs = iris_save_kwargs or {}
    xr_save_kwargs = xr_save_kwargs or {}
    nc4like = Nc4DatasetLike()
    iris.save(
        cubes, nc4like, saver=iris.fileformats.netcdf.save, **iris_save_kwargs
    )
    xrds = to_xarray(**xr_save_kwargs)
    return xrds
