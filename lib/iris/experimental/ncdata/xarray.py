# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""
Wrapper classes containing NcData, which provide an interface to read/write from an
:class:`xarray.Dataset`.

This embeds a certain amount of Xarray knowledge (and dependency), hopefully a minimal
amount.  The structure of an NcData object makes it fairly painless.

"""
from pathlib import Path
from typing import AnyStr, Union

import xarray as xr

from ._core import NcAttribute, NcData, NcDimension, NcVariable


class _XarrayNcDataStore:  # (xr.backends.common.AbstractWritableDataStore)
    # An interface class providing a subset of the
    # :class:`xr.AbstractWriteableDataStore` interface, and which converts to/from a
    # contained ncdata.NcData.
    # This requires some knowledge of Xarray, but it is very small.
    #
    # This code pinched from @TomekTrzeciak
    # see https://gist.github.com/TomekTrzeciak/b00ff6c9dc301ed6f684990e400d1435

    def __init__(self, ncdata: NcData = None):
        if ncdata is None:
            ncdata = NcData()
        self.ncdata = ncdata

    def load(self):
        variables = {}
        for k, v in self.ncdata.variables.items():
            attrs = {
                name: attr._as_python_value()
                for name, attr in v.attributes.items()
            }
            xr_var = xr.Variable(
                v.dimensions, v.data, attrs, getattr(v, "encoding", {})
            )
            # TODO: ?possibly? need to apply usual Xarray "encodings" to convert raw
            #  cf-encoded data into 'normal', interpreted xr.Variables.
            xr_var = xr.conventions.decode_cf_variable(k, xr_var)
            variables[k] = xr_var
        attributes = {
            name: attr._as_python_value()
            for name, attr in self.ncdata.attributes.items()
        }
        return variables, attributes

    def store(
        self,
        variables,
        attributes,
        check_encoding_set=frozenset(),
        writer=None,
        unlimited_dims=None,
    ):
        for attrname, v in attributes.items():
            if (
                attrname in self.ncdata.attributes
            ):  # and self.attributes[k] != v:
                msg = (
                    f're-setting of attribute "{attrname}" : '
                    f"was={self.ncdata.attributes[attrname]}, now={v}"
                )
                raise ValueError(msg)
            else:
                self.ncdata.attributes[attrname] = NcAttribute(attrname, v)

        for varname, var in variables.items():
            if varname in self.ncdata.variables:
                raise ValueError(f'duplicate variable : "{varname}"')

            # An xr.Variable : remove all the possible Xarray encodings
            # These are all the ones potentially used by
            # :func:`xr.conventions.decode_cf_variable`, in the order in which they
            # would be applied.
            var = xr.conventions.encode_cf_variable(
                var, name=varname, needs_copy=False
            )

            for dim_name, size in zip(var.dims, var.shape):
                if dim_name in self.ncdata.dimensions:
                    if self.ncdata.dimensions[dim_name].size != size:
                        raise ValueError(
                            f"size mismatch for dimension {dim_name!r}: "
                            f"{self.ncdata.dimensions[dim_name]} != {size}"
                        )
                else:
                    self.ncdata.dimensions[dim_name] = NcDimension(
                        dim_name, size=size
                    )

            attrs = {
                name: NcAttribute(name, value)
                for name, value in var.attrs.items()
            }
            nc_var = NcVariable(
                name=varname,
                dimensions=var.dims,
                attributes=attrs,
                data=var.data,
                group=self.ncdata,
            )
            self.ncdata.variables[varname] = nc_var

    def close(self):
        pass

    #
    # This interface supports conversion to+from an xarray "Dataset".
    # N.B. using the "AbstractDataStore" interface preserves variable contents, being
    # either real or lazy arrays.
    #
    @classmethod
    def from_xarray(
        cls, dataset_or_file: Union[xr.Dataset, AnyStr, Path], **xr_load_kwargs
    ):
        if not isinstance(dataset_or_file, xr.Dataset):
            # It's a "file" (or pathstring, or Path ?).
            dataset_or_file = xr.load_dataset(
                dataset_or_file, **xr_load_kwargs
            )
        nc_data = cls()
        dataset_or_file.dump_to_store(nc_data, **xr_load_kwargs)
        return nc_data

    def to_xarray(self, **xr_save_kwargs) -> xr.Dataset:
        ds = xr.Dataset.load_store(self, **xr_save_kwargs)
        return ds


def to_xarray(ncdata: NcData) -> xr.Dataset:
    return _XarrayNcDataStore(ncdata).to_xarray()


def from_xarray(xrds: Union[xr.Dataset, Path, AnyStr]) -> NcData:
    return _XarrayNcDataStore.from_xarray(xrds).ncdata
