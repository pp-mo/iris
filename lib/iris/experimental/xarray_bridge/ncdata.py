# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""
An abstract representation of Netcdf data with groups, variables + attributes

This is also provided with a read/write conversion interface to Xarray.

TODO: add direct netcdf file interface (easy, but not yet).

"""
from pathlib import Path
from typing import AnyStr, Dict, Optional, Tuple, Union

import numpy as np
import xarray as xr

#
# A totally basic and naive representation of netCDF data.
# The structure supports groups, variables, attributes.
# The sole limitation here is that data and attributes appear as numpy-compatible
# array-like values (though this may include dask.array.Array), and hence their types
# are modelled as np.dtype's.
#


class NcGroup:
    def __init__(
        self,
        name: Optional[str] = None,
        dimensions: Dict[str, "NcDimension"] = None,
        variables: Dict[str, "NcVariable"] = None,
        attributes: Dict[str, "NcAttribute"] = None,
        groups: Dict[str, "NcGroup"] = None,
    ):
        self.name: str = name
        self.dimensions: Dict[str, "NcDimension"] = dimensions or {}
        self.variables: Dict[str, "NcVariable"] = variables or {}
        self.attributes: Dict[str, "NcAttribute"] = attributes or {}
        self.groups: Dict[str, "NcGroup"] = groups or {}


class NcDimension:
    def __init__(self, name: str, size: int = 0):
        self.name: str = name
        self.size: int = size  # N.B. we retain the 'zero size means unlimited'


class NcVariable:
    def __init__(
        self,
        name: str,
        dimensions: Tuple[str] = None,
        data: np.ndarray = None,
        dtype: np.dtype = None,
        attributes: Dict[str, "NcAttribute"] = None,
        group: "NcGroup" = None,
    ):
        self.name = name
        self.dimensions = tuple(dimensions or ())
        if data is not None:
            if not hasattr(data, "dtype"):
                data = np.asanyarray(data)
            dtype = data.dtype
        self.dtype = dtype
        self.data = data  # Supports lazy, and normally provides a dtype
        self.attributes = attributes or {}
        self.group = group

    # # Provide some array-like readonly properties reflected from the data.
    # @property
    # def dtype(self):
    #     return self.data.dtype
    #
    # @property
    # def shape(self):
    #     return self.data.shape


class NcAttribute:
    def __init__(self, name: str, value):
        self.name: str = name
        # Attribute values are arraylike, have dtype
        # TODO: may need to regularise string representations?
        if not hasattr(value, "dtype"):
            value = np.asanyarray(value)
        self.value: np.ndarray = value

    def _as_python_value(self):
        result = self.value
        if result.dtype.kind in ("U", "S"):
            result = str(result)
            if isinstance(result, bytes):
                result = result.decode()
        return result


class NcDataset(NcGroup):
    # An interface class providing an NcGroup which can be converted to/from an
    # xr.Dataset.  This is basically done by adding a small API enabling it to function
    # as an Xarray "AbstractDataStore".
    # This implies some embedded knowledge of Xarray, but it is very small.
    #
    # This code pinched from @TomekTrzeciak
    # see https://gist.github.com/TomekTrzeciak/b00ff6c9dc301ed6f684990e400d1435

    def load(self):
        variables = {}
        for k, v in self.variables.items():
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
            for name, attr in self.attributes.items()
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
            if attrname in self.attributes:  # and self.attributes[k] != v:
                msg = (
                    f're-setting of attribute "{attrname}" : '
                    f"was={self.attributes[attrname]}, now={v}"
                )
                raise ValueError(msg)
            else:
                self.attributes[attrname] = NcAttribute(attrname, v)

        for varname, var in variables.items():
            if varname in self.variables:
                raise ValueError(f'duplicate variable : "{varname}"')

            # An xr.Variable : remove all the possible Xarray encodings
            # These are all the ones potentially used by
            # :func:`xr.conventions.decode_cf_variable`, in the order in which they
            # would be applied.
            var = xr.conventions.encode_cf_variable(
                var, name=varname, needs_copy=False
            )

            for dim_name, size in zip(var.dims, var.shape):
                if dim_name in self.dimensions:
                    if self.dimensions[dim_name].size != size:
                        raise ValueError(
                            f"size mismatch for dimension {dim_name!r}: "
                            f"{self.dimensions[dim_name]} != {size}"
                        )
                else:
                    self.dimensions[dim_name] = NcDimension(
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
                group=self,
            )
            self.variables[varname] = nc_var

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
