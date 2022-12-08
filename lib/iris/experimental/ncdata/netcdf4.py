# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""
Code to read/write between NcData and a :class:`netCF4.Dataset`, or disk file.

"""
from pathlib import Path
from typing import AnyStr, Union

import dask.array as da
import netCDF4 as nc

from iris._lazy_data import as_lazy_data
from iris.fileformats.netcdf import NetCDFDataProxy

from ._core import NcAttribute, NcData, NcDimension, NcVariable


def to_nc4(
    ncdata: NcData, nc4_dataset_or_file: Union[nc.Dataset, Path, AnyStr]
):
    """
    Write an NcData to a provided (writeable) :class:`netCDF4.Dataset`, or filepath.
    """
    caller_owns_dataset = hasattr(nc4_dataset_or_file, "variables")
    if caller_owns_dataset:
        nc4ds = nc4_dataset_or_file
    else:
        nc4ds = nc.Dataset(nc4_dataset_or_file, "w")

    try:
        for dimname, dim in ncdata.dimensions.items():
            nc4ds.createDimension(dimname, dim.size)

        for varname, var in ncdata.variables.items():
            fillattr = "_FillValue"
            if fillattr in var.attributes:
                fill_value = var.attributes[fillattr].value
            else:
                fill_value = None

            nc4var = nc4ds.createVariable(
                varname=varname,
                datatype=var.dtype,
                dimensions=var.dimensions,
                fill_value=fill_value
                # TODO: needs **kwargs
            )

            data = var.data
            if hasattr(data, "compute"):
                da.store(data, nc4var)
            else:
                nc4var[:] = data

            for attrname, attr in var.attributes.items():
                if attrname != "_FillValue":
                    nc4var.setncattr(attrname, attr._as_python_value())

        for attrname, attr in ncdata.attributes.items():
            nc4ds.setncattr(attrname, attr._as_python_value())

    finally:
        if not caller_owns_dataset:
            nc4ds.close()


def from_nc4(
    nc4_dataset_or_file: Union[nc.Dataset, nc.Group, Path, AnyStr]
) -> NcData:
    """
    Read an NcData from a provided :class:`netCDF4.Dataset`, or filepath.
    """
    ncdata = NcData()
    caller_owns_dataset = hasattr(nc4_dataset_or_file, "variables")
    if caller_owns_dataset:
        nc4ds = nc4_dataset_or_file
    else:
        nc4ds = nc.Dataset(nc4_dataset_or_file)

    try:
        for dimname, nc4dim in nc4ds.dimensions.items():
            ncdata.dimensions[dimname] = NcDimension(dimname, nc4dim.size)

        for varname, nc4var in nc4ds.variables.items():
            var = NcVariable(
                name=varname,
                dimensions=nc4var.dimensions,
                dtype=nc4var.dtype,
                group=ncdata,
            )
            ncdata.variables[varname] = var

            # Assign a data object : for now, always LAZY.
            # code shamelessly stolen from iris.fileformats.netcdf
            fill_value = getattr(
                var,
                "_FillValue",
                nc.default_fillvals[var.dtype.str[1:]],
            )
            shape = tuple(
                ncdata.dimensions[dimname].size for dimname in var.dimensions
            )
            proxy = NetCDFDataProxy(
                shape=shape,
                dtype=var.dtype,
                path=nc4ds.filepath(),
                variable_name=varname,
                fill_value=fill_value,
            )
            var.data = as_lazy_data(proxy)

            for attrname in nc4var.ncattrs():
                var.attributes[attrname] = NcAttribute(
                    attrname, nc4var.getncattr(attrname)
                )

        for attrname in nc4ds.ncattrs():
            ncdata.attributes[attrname] = NcAttribute(
                attrname, nc4ds.getncattr(attrname)
            )

        # And finally, groups -- by the magic of recursion ...
        for grpname, group in nc4ds.groups.items():
            ncdata.groups[grpname] = from_nc4(nc4ds.groups[grpname])

    finally:
        if not caller_owns_dataset:
            nc4ds.close()

    return ncdata
