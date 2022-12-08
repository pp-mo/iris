# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""
Experimental code fror interchanging data with Xarray .


TODO: replace this with various changes:
  * move Iris-agnostic code outside Iris
      - into its own repo (where it can be better tested)
      - leaving **only** the 'to_xarray' and 'from_xarray' functions.
  * add consistency checking
  * add "direct" netcdf interfacing, i.e. NcDataset.to_nc/from_nc

"""
import iris
from iris.cube import CubeList
import iris.fileformats.netcdf as ifn

from ..ncdata.dataset_like import Nc4DatasetLike
from ..ncdata.xarray import from_xarray as ncdata_from_xarray
from ..ncdata.xarray import to_xarray as ncdata_to_xarray

#
# The primary conversion interfaces
#


def cubes_from_xarray(xrds: "xarray.Dataset", **xr_load_kwargs):  # noqa
    ncdata = ncdata_from_xarray(xrds, **xr_load_kwargs)
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
    xrds = ncdata_to_xarray(nc4like._ncdata, **xr_save_kwargs)
    return xrds
