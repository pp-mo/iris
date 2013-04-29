# (C) British Crown Copyright 2010 - 2012, Met Office
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
'''
Provide grib 1 and 2 phenomenon translations to + from CF terms.

This is done by wrapping 'grib_cf_map.py',
which is in a format provided by the metadata translation project.

Currently supports only these:
* grib1 --> cf
* grib2 --> cf
* cf --> grib2

'''

import collections
import warnings

import numpy as np

from iris.fileformats.grib import grib_cf_map as grcf
import iris.std_names
import iris.unit


class LookupTable(dict):
    """
    Specialised dictionary object for making lookup tables.

    Returns None for unknown keys (instead of raising exception).
    Raises exception for any attempt to change an existing entry,
    (but it is still possible to remove keys)

    """
    def __init__(self, *args, **kwargs):
        self._super = super(LookupTable, self)
        self._super.__init__(*args, **kwargs)

    def __getitem__(self, key):
        if not key in self:
            return None
        return self._super.__getitem__(key)

    def __setitem__(self, key, value):
        if key in self and self[key] is not value:
            raise KeyError('Attempted to set dict[{}] = {}, '
                           'but this is already set to {}.'.format(
                               key, value, self[key]))
        self._super.__setitem__(key, value)


#
# Create a lookup table for Grib1 parameters to CF concepts
#

_GRIB1_CF_TABLE = LookupTable()

_GRIB1_TO_CF_KEY_NAMES = ('table2_version', 'centre_number', 'param_number')
_Grib1ToCfKeyClass = collections.namedtuple('Grib1CfKey',
                                            _GRIB1_TO_CF_KEY_NAMES)

# NOTE: this form is currently used for both Grib1 *and* Grib2
_GRIB_TO_CF_DATA_NAMES = ('standard_name', 'long_name', 'units', 'set_height')
_GribToCfDataClass = collections.namedtuple('Grib1CfData',
                                            _GRIB_TO_CF_DATA_NAMES)


def _add_grib1_cf_entry(table2_version, centre_number, param_number,
                        standard_name, long_name, units, set_height=None):
    """
    Check data, convert types and create a new _GRIB1_CF_TABLE row.

    Note that set_height is an optional parameter.  Used to denote phenomena
    that include a height definition (agl), e.g. "2-metre tempererature".

    """
    grib1_key = _Grib1ToCfKeyClass(table2_version=int(grib1data.t2version),
                                   centre_number=int(grib1data.centre),
                                   param_number=int(grib1data.iParam))
    if standard_name is not None:
        if standard_name not in iris.std_names.STD_NAMES:
            warnings.warn('{} is not a recognised CF standard name '
                          '(skipping).'.format(standard_name))
            return
    # convert units string to iris Unit (i.e. mainly, check it is good)
    iris_units = iris.unit.Unit(cfdata.unit)
    # convert height to float : use np.NaN for no set height
    height = float(set_height) if set_height is not None else np.NaN
    cf_data = _GribToCfDataClass(standard_name=cfdata.standard_name,
                                 long_name=cfdata.long_name,
                                 units=iris_units,
                                 set_height=height)
    _GRIB1_CF_TABLE[grib1_key] = cf_data

# Interpret the imported Grib1-to-CF table into a lookup table
for (grib1data, cfdata) in grcf.GRIB1Local_TO_CF.iteritems():
    assert grib1data.edition == 1
    _add_grib1_cf_entry(table2_version=int(grib1data.t2version),
                        centre_number=int(grib1data.centre),
                        param_number=int(grib1data.iParam),
                        standard_name=cfdata.standard_name,
                        long_name=cfdata.long_name,
                        units=cfdata.unit)

# Do the same for special Grib1 codes that include an implied height level
for (grib1data, (cfdata, extra_dimcoord)) \
        in grcf.GRIB1LocalConstrained_TO_CF.iteritems():
    assert grib1data.edition == 1
    if extra_dimcoord.standard_name != 'height':
        raise ValueError('Got implied dimension coord of "{}", '
                         'currently can only handle "height".'.format(
                             extra_dimcoord.standard_name))
    if extra_dimcoord.units != 'm':
        raise ValueError('Got implied dimension units of "{}", '
                         'currently can only handle "m".'.format(
                             extra_dimcoord.units))
    if len(extra_dimcoord.points) != 1:
        raise ValueError('Implied dimension has {} points, '
                         'currently can only handle 1.'.format(
                             len(extra_dimcoord.points)))
    _add_grib1_cf_entry(table2_version=int(grib1data.t2version),
                        centre_number=int(grib1data.centre),
                        param_number=int(grib1data.iParam),
                        standard_name=cfdata.standard_name,
                        long_name=cfdata.long_name,
                        units=cfdata.unit,
                        set_height=extra_dimcoord.points[0])


#
# Create a lookup table for Grib2 parameters to CF concepts
#

_GRIB2_CF_TABLE = LookupTable()

_GRIB2_TO_CF_KEY_NAMES = ('param_discipline', 'param_category', 'param_number')
_Grib2ToCfKeyClass = collections.namedtuple('Grib2CfKey',
                                            _GRIB2_TO_CF_KEY_NAMES)


def _add_grib2_cf_entry(param_discipline, param_category, param_number,
                        standard_name, long_name, units):
    """
    Check data, convert types and create a new _GRIB2_CF_TABLE row.

    Note that set_height is an optional parameter.  Used to denote phenomena
    that include a height definition (agl), e.g. "2-metre tempererature".

    """
    grib2_key = _Grib2ToCfKeyClass(param_discipline=int(param_discipline),
                                   param_category=int(param_category),
                                   param_number=int(param_number))
    if standard_name is not None:
        if standard_name not in iris.std_names.STD_NAMES:
            warnings.warn('{} is not a recognised CF standard name '
                          '(skipping).'.format(standard_name))
            return
    # convert units string to iris Unit (i.e. mainly, check it is good)
    iris_units = iris.unit.Unit(cfdata.unit)
    cf_data = _GribToCfDataClass(standard_name=cfdata.standard_name,
                                 long_name=cfdata.long_name,
                                 units=iris_units,
                                 set_height=np.NaN)
    _GRIB2_CF_TABLE[grib2_key] = cf_data


for cfdata, grib2data in grcf.CF_TO_GRIB2.iteritems():
    assert grib2data.edition == 2
    _add_grib2_cf_entry(param_discipline=int(grib2data.discipline),
                        param_category=int(grib2data.category),
                        param_number=int(grib2data.number),
                        standard_name=cfdata.standard_name,
                        long_name=cfdata.long_name,
                        units=cfdata.unit)


#
# Create a lookup table for CF names to Grib2 concepts
#
_CF_GRIB2_TABLE = LookupTable()

_CF_TO_GRIB2_KEY_NAMES = ('standard_name', 'long_name')
_CfToGrib2KeyClass = collections.namedtuple('CfGrib2Key',
                                            _CF_TO_GRIB2_KEY_NAMES)

_CF_TO_GRIB2_DATA_NAMES = ('discipline', 'category', 'number', 'units')
_CfToGrib2DataClass = collections.namedtuple('CfGrib2Data',
                                             _CF_TO_GRIB2_DATA_NAMES)


def _add_cf_grib2_entry(standard_name, long_name,
                        param_discipline, param_category, param_number, units):
    """ Check data, convert types and create a new _CF_TABLE row. """
    assert standard_name is not None or long_name is not None
    if standard_name is not None:
        long_name = None
        if standard_name not in iris.std_names.STD_NAMES:
            warnings.warn('{} is not a recognised CF standard name '
                          '(skipping).'.format(standard_name))
            return
    cf_key = _CfToGrib2KeyClass(standard_name, long_name)
    # convert units string to iris Unit (i.e. mainly, check it is good)
    iris_units = iris.unit.Unit(cfdata.unit)
    grib2_data = _CfToGrib2DataClass(discipline=int(param_discipline),
                                     category=int(param_category),
                                     number=int(param_number),
                                     units=iris_units)
    _GRIB2_CF_TABLE[cf_key] = grib2_data


# Interpret the imported CF-to-Grib2 table into a lookup table
for cfdata, grib2data in grcf.CF_TO_GRIB2.iteritems():
    assert grib2data.edition == 2
    iris_units = iris.unit.Unit(cfdata.unit)
    _add_cf_grib2_entry(standard_name=cfdata.standard_name,
                        long_name=cfdata.long_name,
                        param_discipline=grib2data.discipline,
                        param_category=grib2data.category,
                        param_number=grib2data.number,
                        units=iris_units)


#
# Main interface functions for translation lookups
#

def grib1_phenom_to_cf_info(table2_version, centre_number, param_number):
    """
    Lookup grib-1 parameter --> cf_data or None.

    Returned cf_data has attributes:
    * standard_name
    * long_name
    * units : a :class:`iris.unit.Unit`
    * set_height :  a scalar 'height' value , or np.NaN

    """
    grib1_key = _Grib1ToCfKeyClass(table2_version=table2_version,
                                   centre_number=centre_number,
                                   param_number=param_number)
    return _GRIB1_CF_TABLE[grib1_key]


def grib2_phenom_to_cf_info(param_discipline, param_category, param_number):
    """
    Lookup grib-2 parameter --> cf_data or None.

    Returned cf_data has attributes:
    * standard_name
    * long_name
    * units : a :class:`iris.unit.Unit`

    """
    grib2_key = _Grib2ToCfKeyClass(param_discipline=int(param_discipline),
                                   param_category=int(param_category),
                                   param_number=int(param_number))
    return _GRIB2_CF_TABLE[grib2_key]


def cf_phenom_to_grib2_info(standard_name, long_name=None):
    """
    Lookup CF names --> grib2_data or None.

    Returned grib2_data has attributes:
    * discipline
    * category
    * number
    * units : a :class:`iris.unit.Unit`
        The unit represents the defined reference units for the message data.

    """
    if standard_name is not None:
        long_name = None
    return _GRIB2_CF_TABLE[(standard_name, long_name)]
