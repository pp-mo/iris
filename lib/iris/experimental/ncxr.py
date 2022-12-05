# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""
Temporary code layer supporting interoperation between Iris and Xarray.

TODO: replace this with various changes:
  * move Iris-agnostic code outside Iris
      - into its own repo (where it can be better tested)
      - leaving **only** the 'to_xarray' and 'from_xarray' functions.
  * add consistency checking
  * add "direct" netcdf interfacing, i.e. NcDataset.to_nc/from_nc

"""
from functools import wraps
from pathlib import Path  # noqa
from typing import AnyStr, Dict, Optional, Tuple, Union

import dask.array as da
import netCDF4
import numpy as np
import xarray as xr

import iris
from iris.cube import CubeList
import iris.fileformats.netcdf
import iris.tests as itsts

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
            if k == "time":
                t_bdg = 0
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
        for k, v in attributes.items():
            if k in self.attributes:  # and self.attributes[k] != v:
                msg = (
                    f're-setting of attribute "{k}" : '
                    f"was={self.attributes[k]}, now={v}"
                )
                raise ValueError(msg)
            else:
                self.attributes[k] = NcAttribute(k, v)
        for k, v in variables.items():
            if hasattr(v, "ncattrs"):
                # An actual netCDF.Variable (?PP, not sure?)
                data, dtype, dims, attrs, enc = (
                    v[:],
                    v.datatype,
                    v.dimensions,
                    v.ncattrs(),
                    getattr(v, "encoding", {}),
                )
            else:
                # An xr.Variable (?PP, not sure?)
                # remove all the possible Xarray encodings
                # These are all the ones potentially used by
                # :func:`xr.conventions.decode_cf_variable`, in the order in which they
                # would be applied.
                v = xr.conventions.encode_cf_variable(
                    v, name=k, needs_copy=False
                )
                data, dtype, dims, attrs, enc = (
                    v.data,
                    v.dtype,
                    v.dims,
                    v.attrs,
                    v.encoding,
                )

            for dim_name, size in zip(dims, v.shape):
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

            if k in self.variables:
                raise ValueError(f'duplicate variable : "{k}"')
            attrs = {
                name: NcAttribute(name, value) for name, value in attrs.items()
            }
            nc_var = NcVariable(
                name=k,
                dimensions=dims,
                attributes=attrs,
                data=v.data,
                group=self,
            )
            self.variables[k] = nc_var

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


#
# Classes containing NcDataset and NcVariables, but emulating the access APIs of a
# netCDF4.Dataset.
# Notes:
#   (1) only supports what is required for Iris load/save capability
#   (2) we are proposing that this remains private, for now? -- due to (1)
#
class _Nc4DatalikeWithNcattrs:
    # A mixin, shared by _Nc4DatasetLike and _Nc4VariableLike, which adds netcdf-like
    #  attribute operations'ncattrs / setncattr / getncattr', *AND* extends the local
    #  objects attribute to those things also
    # N.B. "self._ncdata" is the underlying NcData object : either an NcDataset or
    #  NcVariable object.
    def ncattrs(self):
        return list(self._ncdata.attributes.keys())

    def getncattr(self, attr):
        attrs = self._ncdata.attributes
        if attr in attrs:
            result = attrs[attr]._as_python_value()
        else:
            # Don't allow it to issue a KeyError, as this upsets 'getattr' usage.
            # Raise an AttributeError instead.
            raise AttributeError(attr)
        return result

    def setncattr(self, attr, value):
        # TODO: are we sure we need this translation ??
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        # N.B. using the NcAttribute class for storage also ensures/requires that all
        #  attributes are cast as numpy arrays (so have shape, dtype etc).
        self._ncdata.attributes[attr] = NcAttribute(attr, value)

    def __getattr__(self, attr):
        # Extend local object attribute access to the ncattrs of the stored data item
        #  (Yuck, but I think the Iris load code requires it).
        return self.getncattr(attr)

    def __setattr__(self, attr, value):
        if attr in self._local_instance_props:
            # N.B. use _local_instance_props to define standard instance attributes, to avoid a
            #  possible endless loop here.
            super().__setattr__(attr, value)
        else:
            # # if not hasattr(self, '_allsetattrs'):
            # #     self._allsetattrs = set()
            # self._allsetattrs.add(attr)
            self.setncattr(attr, value)


class _Nc4DatasetLike(_Nc4DatalikeWithNcattrs):
    _local_instance_props = ("_ncdata", "variables")

    def __init__(self, ncdata: NcDataset = None):
        if ncdata is None:
            ncdata = NcDataset()  # an empty dataset
        self._ncdata = ncdata
        # N.B. we need to create + store our OWN variables, as they are wrappers for
        #  the underlying NcVariable objects, with different properties.
        self.variables = {
            name: _Nc4VariableLike._from_ncvariable(ncvar, group=self)
            for name, ncvar in self._ncdata.variables.items()
        }

    @property
    def dimensions(self):
        return {
            name: dim.size for name, dim in self._ncdata.dimensions.items()
        }

    # @property
    # def attributes(self):
    #     return {
    #         name: attr.value
    #         for name, attr in self.ncdata.attributes.items()
    #     }

    @property
    def groups(self):
        return None  # not supported

    # def ncattrs(self):
    #     return self.attributes
    #
    # def getncattr(self, attr_name):
    #     if attr_name in self.attributes:
    #         return self.attributes[attr_name]
    #     raise AttributeError(attr_name)
    #
    # def setncattr(self, attr_name, value):
    #     if isinstance(value, bytes):
    #         value = value.decode("utf-8")
    #     self.ncdata.attributes[attr_name] = NcAttribute(attr_name, value)
    #
    # Attributes other than the instance-defining "slots" translate to netcdf
    #  attributes of the underlying ncdata varable
    #
    def createDimension(self, dimname, size):
        if dimname in self.dimensions:
            msg = f'creating duplicate dimension "{dimname}".'
            raise ValueError(msg)
            # if self.dimensions[name] != size:
            #     raise ValueError(f"size mismatch for dimension {name!r}: "
            #                      f"{self.dimensions[name]} != {size}")
        else:
            self._ncdata.dimensions[dimname] = NcDimension(dimname, size)
        return size

    def createVariable(self, varname, datatype, dimensions=(), **encoding):
        if varname in self.variables:
            msg = f'creating duplicate variable "{varname}".'
            raise ValueError(msg)
        # Add a variable into the underlying NcDataset object.
        ncvar = NcVariable(
            name=varname,
            dimensions=dimensions,
            group=self._ncdata,
        )
        # Note: initially has no data (or attributes), since this is how netCDF4 expects
        #  to do it.
        self._ncdata.variables[varname] = ncvar
        # Create a netCDF4-like "wrapper" variable + install that here.
        nc4var = _Nc4VariableLike._from_ncvariable(
            ncvar, group=self, dtype=datatype
        )
        self.variables[varname] = nc4var
        return nc4var

    def sync(self):
        pass
        # for k, v in self.variables.items():
        #     if not hasattr(v, 'data'):
        #         # coordinate system variables are created but not initialized with data by Iris!
        #         v.data = np.empty(v.shape, dtype=v.datatype)
        #         v.data[...] = netCDF4.default_fillvals.get(np.dtype(v.datatype).str[1:])

    def close(self):
        self.sync()

    def filepath(self):
        #
        # Note: for now, let's just not care about this.
        # we *might* need this to be an optinoal defined item on an NcDataset ??
        # .. or, we ight need to store an xarray "encoding" somewhere ?
        #
        # return self.ncdata.encoding.get("source", "")
        return "<Nc4DatasetLike>"


class _Nc4VariableLike(_Nc4DatalikeWithNcattrs):
    _local_instance_props = ("_ncdata", "name", "datatype", "_raw_array")

    def __init__(self, ncvar: NcVariable, datatype: np.dtype):
        self._ncdata = ncvar
        self.name = ncvar.name
        # Note: datatype must be known at creation, which may be before an actual data
        #  array is assigned on the ncvar.
        self.datatype = np.dtype(datatype)
        if ncvar.data is None:
            # temporary empty data (to support never-written scalar values)
            ncvar.data = np.zeros(self.shape, self.datatype)
        self[:] = ncvar.data

    @classmethod
    def _from_ncvariable(
        cls, ncvar: NcVariable, group: NcGroup, dtype: np.dtype = None
    ):
        if dtype is None:
            dtype = ncvar.dtype
        self = cls(
            ncvar=ncvar,
            datatype=dtype,
        )
        return self

    # Label this as an 'emulated' netCDF4.Variable, containing an actual (possibly
    #  lazy) array, which can be directly read/written.
    @property
    def _raw_array(self):
        return self._ncdata.data

    @_raw_array.setter
    def _raw_array(self, data):
        self._ncdata.data = data
        self.datatype = data.dtype

    @property
    def group(self):
        return self._ncdata.group

    @property
    def dimensions(self):
        return self._ncdata.dimensions

    #
    # "Normal" data access is via indexing.
    #
    def __getitem__(self, keys):
        if keys != slice(None):
            raise IndexError(keys)
        if self.ndim == 0:
            return self._ncdata.data
        return self._ncdata.data[keys]

    def __setitem__(self, keys, data):
        if keys != slice(None):
            raise IndexError(keys)
        if not hasattr(data, "dtype"):
            raise ValueError(f"nonarray assigned as data : {data}")
        if not data.shape == self.shape:
            msg = (
                f"assigned data has wrong shape : "
                f"{data.shape} instead of {self.shape}"
            )
            raise ValueError(msg)
        self._ncdata.data = data
        self.datatype = data.dtype
        # if not self.dimensions and data.ndim != 0:
        #     # Iris assigns 1-D single element array to 0-D var!
        #     self.data = np.asarray(data.item())
        # else:
        #     shape = tuple(self.group.dimensions[d] for d in self.dimensions)
        #     if data.shape != shape:
        #         # Iris passes bounds arrays of wrong shape!
        #         self.data = data.reshape(shape)
        #     else:
        #         self.data = data

    @property
    def dtype(self):
        return self.datatype

    @property
    def dims(self):
        return self.dimensions

    @property
    def ndim(self):
        return len(self.dimensions)

    @property
    def shape(self):
        dims = self.group.dimensions
        return tuple(dims[n].size for n in self.dimensions)

    @property
    def size(self):
        return np.prod(self.shape)

    def chunking(self):
        return None


def cubes_from_xrds(xrds: xr.Dataset, **xr_load_kwargs):
    ncdata = NcDataset.from_xarray(xrds, **xr_load_kwargs)
    dslike = _Nc4DatasetLike(ncdata)
    cubes = CubeList(iris.fileformats.netcdf.load_cubes(dslike))
    return cubes


def cubes_to_xrds(cubes, iris_save_kwargs=None, xr_save_kwargs=None):
    iris_save_kwargs = iris_save_kwargs or {}
    xr_save_kwargs = xr_save_kwargs or {}
    nc4like = _Nc4DatasetLike()
    iris.save(
        cubes, nc4like, saver=iris.fileformats.netcdf.save, **iris_save_kwargs
    )
    xrds = nc4like._ncdata.to_xarray(**xr_save_kwargs)
    return xrds


def example_from_xr():
    iris.FUTURE.datum_support = True
    filepath = itsts.get_data_path(
        ["NetCDF", "stereographic", "toa_brightness_temperature.nc"]
    )
    xrds = xr.open_dataset(filepath, chunks="auto")
    print("\nOriginal Xarray dataset:\n", xrds)
    cubes = cubes_from_xrds(xrds)
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
    xrds2 = cubes_to_xrds(cubes)
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
