# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""
An adaptor layer allowing an NcData to masquerade as a netCDF4.Dataset object.

This is provided primarily to support a re-use of the iris.fileformats.netcdf file
format load + save, to convert cubes to+from ncdata objects, and hence convert Iris
 cubes to+from an xarray.Dataset.

These classes contain NcDataset and NcVariables, but emulating the access APIs of a
netCDF4.Dataset.

Note: currently only supports what is required for Iris load/save capability.
It could conceivably be used for data exchange by *other* code that reads or writes
netcdf files, but that may require API support to be extended, depending on what
additional methods might be used.

"""
import numpy as np

from ._core import NcAttribute, NcDataset, NcDimension, NcVariable


class _Nc4DatalikeWithNcattrs:
    # A mixin, shared by Nc4DatasetLike and Nc4VariableLike, which adds netcdf-like
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


class Nc4DatasetLike(_Nc4DatalikeWithNcattrs):
    _local_instance_props = ("_ncdata", "variables")

    def __init__(self, ncdata: NcDataset = None):
        if ncdata is None:
            ncdata = NcDataset()  # an empty dataset
        self._ncdata = ncdata
        # N.B. we need to create + store our OWN variables, as they are wrappers for
        #  the underlying NcVariable objects, with different properties.
        self.variables = {
            name: Nc4VariableLike._from_ncvariable(ncvar)
            for name, ncvar in self._ncdata.variables.items()
        }

    @property
    def dimensions(self):
        return {
            name: dim.size for name, dim in self._ncdata.dimensions.items()
        }

    @property
    def groups(self):
        return None  # not supported

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
        nc4var = Nc4VariableLike._from_ncvariable(ncvar, dtype=datatype)
        self.variables[varname] = nc4var
        return nc4var

    def sync(self):
        pass

    def close(self):
        self.sync()

    @staticmethod
    def filepath():
        #
        # Note: for now, let's just not care about this.
        # we *might* need this to be an optinoal defined item on an NcDataset ??
        # .. or, we ight need to store an xarray "encoding" somewhere ?
        # TODO: more thought here ?
        # return self.ncdata.encoding.get("source", "")
        return "<Nc4DatasetLike>"


class Nc4VariableLike(_Nc4DatalikeWithNcattrs):
    _local_instance_props = ("_ncdata", "name", "datatype", "_raw_array")

    def __init__(self, ncvar: NcVariable, datatype: np.dtype):
        self._ncdata = ncvar
        self.name = ncvar.name
        # Note: datatype must be known at creation, which may be before an actual data
        #  array is assigned on the ncvar.
        self.datatype = np.dtype(datatype)
        if ncvar.data is None:
            # temporary empty data (to support never-written scalar values)
            # NOTE: significantly, does *not* allocate an actual full array in memory
            array = np.zeros(self.shape, self.datatype)
            ncvar.data = array
        self._raw_array = ncvar.data

    @classmethod
    def _from_ncvariable(cls, ncvar: NcVariable, dtype: np.dtype = None):
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
    # N.B. we do still need to support this, e.g. for DimCoords ?
    #
    def __getitem__(self, keys):
        if keys != slice(None):
            raise IndexError(keys)
        if self.ndim == 0:
            return self._ncdata.data
        return self._ncdata.data[keys]

    # The __setitem__ is not required for normal saving.
    # The saver will assign ._raw_array instead
    # TODO: might need to support this for future non-Iris usage ?
    #
    # def __setitem__(self, keys, data):
    #     if keys != slice(None):
    #         raise IndexError(keys)
    #     if not hasattr(data, "dtype"):
    #         raise ValueError(f"nonarray assigned as data : {data}")
    #     if not data.shape == self.shape:
    #         msg = (
    #             f"assigned data has wrong shape : "
    #             f"{data.shape} instead of {self.shape}"
    #         )
    #         raise ValueError(msg)
    #     self._ncdata.data = data
    #     self.datatype = data.dtype

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
