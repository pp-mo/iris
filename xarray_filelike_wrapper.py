"""
Module for wrapping an :class:`ncobj.Group` to make it as far as
possible appear as if it were a :class:`netCDF4.Dataset`.
This is for read-only purposes : all dataset-changing methods are missing.

At present this is focussed on delivering the ability to load these
quasi-datasets into the Iris project (https://github.com/SciTools/iris) :
The emulation of any behaviours *not* used there are currently uncertain.

"""
from collections import OrderedDict

import xarray as xr


def variable_original_style(xr_variable):
    """
    Return the attributes of an xarray Variable, with special handling in the
    case that it contains time-based values :  That is, in that case we need
    to "reconstruct" the original 'units' and/or 'calendar' attributes.

    Args:

    * xr_variable (:class:`xarray.Variable`):
        input variable

    Returns:

    * reformed_variable (:class:`xarray.Variable`):
        Variable as input : If a time-unit coord, this will contain the
        'original form' data, units and calendar.

    """
    if hasattr(xr_variable, 'data'):
        # This bit for coords + data_vars, but not dataset (i.e. global attrs)
        xr_variable = CFTimedeltaCoder().encode(
            CFDatetimeCoder().encode(xr_variable))
    return xr_variable


class Nc4ComponentLike(object):
    """
    Abstract class providing general methods for all Nc4ComponentLike
    object types.

    """
    def __init__(self, xarray_object, parent_grp=None):
        """Create an object wrapping an Xarray object."""
        self._xrobj = xarray_object
        #: parent group object (Like)
        self._parent_group_ncobj = parent_grp

    @property
    def name(self):
        return self._xrobj.name

    def group(self):
        return self._parent_group_ncobj

    def __eq__(self, other):
        return self._xrobj == other._xrobj

    def __ne__(self, other):
        return not self == other


def _name_as_string(obj_or_string):
    return (obj_or_string.name
            if hasattr(obj_or_string, 'name')
            else obj_or_string)


class DimensionLike(object):
    """
    A DimensionLike object wrapper.

    Dimension properties: name, length, unlimited, (+ parent-group)

    """
    def __init__(self, name, length, unlimited):
        self.name = name
        self.size = length
        self.is_unlimited = unlimited

    def __len__(self):
        return self.size

    def isunlimited(self):
        return self.is_unlimited


class Nc4ComponentAttrsLike(Nc4ComponentLike):
    """An abstract class for an Nc4ComponentLike with attribute access."""
    def __init__(self, xarray_object, *args, **kwargs):
        """Create an object wrapping an Xarray object."""
        xarray_object = variable_original_style(xarray_object)
        super(Nc4ComponentAttrsLike, self).__init__(
            xarray_object, *args, **kwargs)

        # Get back our 'original' "coordinates" attribute.
        if hasattr(self._xrobj, 'encoding'):
            coords = self._xrobj.encoding.get('coordinates', '')
        self._xrobj.attrs['coordinates'] = coords

    def ncattrs(self):
        return self._xrobj.attrs

    def getncattr(self, attr_name):
        if attr_name in self._xrobj.attrs:
            result = self._xrobj.attrs[attr_name]
        else:
            raise AttributeError()
        return result

    def __getattr__(self, attr_name):
        return self.getncattr(attr_name)


class VariableLike(Nc4ComponentAttrsLike):
    """
    A VariableLike object wrapper.

    Variable properties:
        name, dimensions, dtype, data (+ attributes, parent-group)
        shape, size, ndim

    """
    @property
    def dtype(self):
        return self._xrobj.dtype

    @property
    def datatype(self):
        return self.dtype

    @property
    def dimensions(self):
        return tuple(map(_name_as_string, self._xrobj.dims))

    def __getitem__(self, keys):
        if self.ndim == 0:
            return self._xrobj.data
        else:
            return self._xrobj.data[keys]

    @property
    def shape(self):
        return self._xrobj.shape

    @property
    def ndim(self):
        return self._xrobj.ndim

    @property
    def size(self):
        return self._xrobj.size

    def chunking(self):
        chunks = None
        if hasattr(self._xrobj, 'encoding'):
            chunks = self._xrobj.encoding.get('chunksizes', None)
        return chunks


class GroupLike(Nc4ComponentAttrsLike):
    """
    A GroupLike object wrapper.

    Group properties:
        name, dimensions, variables, (sub)groups (+ attributes, parent-group)

    """
    def __init__(self, *args, **kwargs):
        super(GroupLike, self).__init__(*args, **kwargs)
        self._precaching_dims = True
        self._reread_components()

    def _reread_components(self):        
        # Dims: NOTE xarray does not store/presevere unlimited aspect of dims.
        self.dimensions = OrderedDict(
            [(name,
			  DimensionLike(name,
						    length=self._xrobj.dims[name],
						    unlimited=False))
             for name in self._xrobj.dims.keys()])

        # Vars
        self.variables = OrderedDict(
            [(name, VariableLike(self._xrobj.variables[name], parent_grp=self))
             for name in self._xrobj.variables.keys()])

        # Groups (probably unused!)
        self.groups = OrderedDict()
#            [(grp.name, GroupLike(grp, parent_grp=self))
#             for grp in self._xrobj.groups])

    def createDimension(self, dim_name, size, unlimited=False):
        if not self._precaching_dims:
            raise ValueError('dataset already initialised.')
        
        self._xrobj.dims[dim_name] = size


    def createVariable(self, varname, datatype, dimensions=(),
                       zlib=False, complevel=4, shuffle=True,
                       fletcher32=False, contiguous=False, chunksizes=None,
                       endian='native', least_significant_digit=None,
                       fill_value=None):
        if self._precaching_dims:
            # replace underlying object with one of the required dimensions. 
            self._xrobj = xr.Dataset(data_vars, coords, attrs, compat)
        else:
            # add an additional variable.
            self._xrobj[varname] = xr.Variable(
                dims=dimensions,
                data=, attrs, encoding, fastpath)


class Nc4DatasetLike(GroupLike):
    def close(self):
        # ?should we not be doing "something" here ??
        return

    def sync(self):
        pass


def fake_nc4python_dataset(xarray_dataset):
    """
    Make a wrapper around an xarray Dataset object to emulate a
    :class:`netCDF4.Dataset'.

    The resulting :class:`GroupLike` supports the essential properties of a
    read-mode :class:`netCDF4.Dataset', enabling an arbitrary netcdf data
    structure in memory to be "read" as if it were a file
    (i.e. without writing it to disk).

    In particular, variable data access is delegated to the original,
    underlying :class:`ncobj.Group` object :  This provides deferred, sectional
    data access on request, in the usual way, avoiding the need to read in all
    the variable data.

    """
    return Nc4DatasetLike(xarray_dataset)
