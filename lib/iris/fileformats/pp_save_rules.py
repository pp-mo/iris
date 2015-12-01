# (C) British Crown Copyright 2013 - 2015, Met Office
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
#
"""
PP save rules : originally derived from legacy text rules file,
lib/iris/etc/pp_save_rules.txt

"""
from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa
import six


import warnings

import netcdftime
import numpy as np
import numpy.ma as ma

from iris.fileformats.rules import \
    scalar_coord, vector_coord, scalar_cell_method, \
    has_aux_factory, aux_factory
from iris.util import is_regular, regular_step

from iris.aux_factory import HybridHeightFactory, HybridPressureFactory
from iris.coords import AuxCoord, CellMethod, DimCoord
from iris.fileformats.rules import Factory, Reference, ReferenceTarget
from iris.fileformats.um_cf_map import LBFC_TO_CF, STASH_TO_CF
from iris.unit import Unit
import iris.fileformats.pp
import iris.unit


def conditional_warning(condition, warning):
    pass  # without this pass statement it alsp print, "  Args:" on a new line.
    if condition:
        warnings.warn(warning)


def verify(cm, pp):
    factories = []
    references = []
    standard_name = None
    long_name = None
    units = None
    attributes = {}
    cell_methods = []
    dim_coords_and_dims = []
    aux_coords_and_dims = []

    if True:
        pp.lbproc = 0                # Processing. Start at 0.

    if cm.coord_system("GeogCS") is not None or cm.coord_system(None) is None:
        pp.bplat = 90
        pp.bplon = 0

    if cm.coord_system("RotatedGeogCS") is not None:
        pp.bplat = cm.coord_system("RotatedGeogCS").grid_north_pole_latitude
        pp.bplon = cm.coord_system("RotatedGeogCS").grid_north_pole_longitude

    if \
            (not 'um_version' in cm.attributes) and \
            ('source' in cm.attributes) and \
            (len(cm.attributes['source'].rsplit("Data from Met Office Unified Model", 1)) > 1) and \
            (len(cm.attributes['source'].rsplit("Data from Met Office Unified Model", 1)[1]) == 0):
        pp.lbsrce = 1111

    if \
            (not 'um_version' in cm.attributes) and \
            ('source' in cm.attributes) and \
            (len(cm.attributes['source'].rsplit("Data from Met Office Unified Model", 1)) > 1) and \
            (len(cm.attributes['source'].rsplit("Data from Met Office Unified Model", 1)[1]) > 0):
        pp.lbsrce = int(float(cm.attributes['source'].rsplit("Data from Met Office Unified Model", 1)[1]) * 1000000) + 1111  # UM version

    if 'um_version' in cm.attributes:
        pp.lbsrce = 1111 + 10000 * int(cm.attributes['um_version'].split('.')[1]) + 1000000 * int(cm.attributes['um_version'].split('.')[0])

    if \
            ('STASH' in cm.attributes) and \
            (isinstance(cm.attributes['STASH'], iris.fileformats.pp.STASH)):
        pp.lbuser[3] = 1000 * (cm.attributes['STASH'].section or 0) + (cm.attributes['STASH'].item or 0)
        pp.lbuser[6] = (cm.attributes['STASH'].model or 0)

    if \
            (scalar_coord(cm, 'time') is not None) and \
            (scalar_coord(cm, 'forecast_period') is None) and \
            (scalar_coord(cm, 'forecast_reference_time') is None):
        pp.lbtim.ia = 0
        pp.lbtim.ib = 0
        pp.t1 = scalar_coord(cm, 'time').units.num2date(scalar_coord(cm, 'time').points[0])
        pp.t2 = netcdftime.datetime(0, 0, 0)

    if \
            (scalar_coord(cm, 'time') is not None) and \
            (not scalar_coord(cm, 'time').has_bounds()) and \
            (scalar_coord(cm, 'forecast_period') is not None):
        pp.lbtim.ia = 0
        pp.lbtim.ib = 1
        pp.t1 = scalar_coord(cm, 'time').units.num2date(scalar_coord(cm, 'time').points[0])
        pp.t2 = scalar_coord(cm, 'time').units.num2date(scalar_coord(cm, 'time').points[0] - scalar_coord(cm, 'forecast_period').points[0])
        pp.lbft = scalar_coord(cm, 'forecast_period').points[0]

    if \
            (scalar_coord(cm, 'time') is not None) and \
            (scalar_coord(cm, 'time').has_bounds()) and \
            (scalar_coord(cm, 'clim_season') is None) and \
            (scalar_coord(cm, 'forecast_period') is not None) and \
            (scalar_coord(cm, 'forecast_period').has_bounds()):
        pp.lbtim.ib = 2
        pp.t1 = scalar_coord(cm, 'time').units.num2date(scalar_coord(cm, 'time').bounds[0,0])
        pp.t2 = scalar_coord(cm, 'time').units.num2date(scalar_coord(cm, 'time').bounds[0,1])
        pp.lbft = scalar_coord(cm, 'forecast_period').units.convert(scalar_coord(cm, 'forecast_period').bounds[0, 1], 'hours')

    if \
            (scalar_coord(cm, 'time') is not None) and \
            (scalar_coord(cm, 'time').has_bounds()) and \
            (scalar_coord(cm, 'clim_season') is None) and \
            (scalar_coord(cm, 'forecast_period') is None) and \
            (scalar_coord(cm, 'forecast_reference_time') is not None):
        pp.lbtim.ib = 2
        pp.t1 = scalar_coord(cm, 'time').units.num2date(scalar_coord(cm, 'time').bounds[0,0])
        pp.t2 = scalar_coord(cm, 'time').units.num2date(scalar_coord(cm, 'time').bounds[0,1])
        pp.lbft = scalar_coord(cm, 'time').units.convert(scalar_coord(cm, 'time').bounds[0, 1], 'hours since epoch') - scalar_coord(cm, 'forecast_reference_time').units.convert(scalar_coord(cm, 'forecast_reference_time').points[0], 'hours since epoch')

    if \
            (scalar_coord(cm, 'time') is not None) and \
            (scalar_coord(cm, 'time').has_bounds()) and \
            (scalar_coord(cm, 'clim_season') is None) and \
            (scalar_coord(cm, 'forecast_period') is not None or scalar_coord(cm, 'forecast_reference_time') is not None) and \
            (scalar_cell_method(cm, 'mean', 'time') is not None) and \
            (scalar_cell_method(cm, 'mean', 'time').intervals != ()) and \
            (scalar_cell_method(cm, 'mean', 'time').intervals[0].endswith('hour')):
        pp.lbtim.ia = int(scalar_cell_method(cm, 'mean', 'time').intervals[0][:-5])

    if \
            (scalar_coord(cm, 'time') is not None) and \
            (scalar_coord(cm, 'time').has_bounds()) and \
            (scalar_coord(cm, 'clim_season') is None) and \
            (scalar_coord(cm, 'forecast_period') is not None or scalar_coord(cm, 'forecast_reference_time') is not None) and \
            (scalar_cell_method(cm, 'mean', 'time') is None or scalar_cell_method(cm, 'mean', 'time').intervals == () or not scalar_cell_method(cm, 'mean', 'time').intervals[0].endswith('hour')):
        pp.lbtim.ia = 0

    if \
            (scalar_coord(cm, 'time') is not None) and \
            (scalar_coord(cm, 'time').has_bounds()) and \
            (scalar_coord(cm, 'time').units.num2date(scalar_coord(cm, 'time').bounds[0,0]).year == scalar_coord(cm, 'time').units.num2date(scalar_coord(cm, 'time').bounds[0,1]).year) and \
            (scalar_coord(cm, 'forecast_period') is not None) and \
            (scalar_coord(cm, 'forecast_period').has_bounds()) and \
            (scalar_coord(cm, 'clim_season') is not None) and \
            ('clim_season' in cm.cell_methods[-1].coord_names):
        pp.lbtim.ia = 0
        pp.lbtim.ib = 2
        pp.t1 = scalar_coord(cm, 'time').units.num2date(scalar_coord(cm, 'time').bounds[0, 0])
        pp.t2 = scalar_coord(cm, 'time').units.num2date(scalar_coord(cm, 'time').bounds[0, 1])
        pp.lbft = scalar_coord(cm, 'forecast_period').units.convert(scalar_coord(cm, 'forecast_period').bounds[0, 1], 'hours')

    if \
            (scalar_coord(cm, 'time') is not None) and \
            (scalar_coord(cm, 'time').has_bounds()) and \
            (scalar_coord(cm, 'time').units.num2date(scalar_coord(cm, 'time').bounds[0,0]).year != scalar_coord(cm, 'time').units.num2date(scalar_coord(cm, 'time').bounds[0,1]).year) and \
            (scalar_coord(cm, 'forecast_period') is not None) and \
            (scalar_coord(cm, 'forecast_period').has_bounds()) and \
            (scalar_coord(cm, 'clim_season') is not None) and \
            ('clim_season' in cm.cell_methods[-1].coord_names) and \
            (scalar_coord(cm, 'clim_season').points[0] == 'djf'):
        pp.lbtim.ia = 0
        pp.lbtim.ib = 3
        pp.t1 = scalar_coord(cm, 'time').units.num2date(scalar_coord(cm, 'time').bounds[0,0])
        pp.t2 = scalar_coord(cm, 'time').units.num2date(scalar_coord(cm, 'time').bounds[0,1])
        pp.t1 = netcdftime.datetime( pp.t1.year if pp.t1.month==12 else pp.t1.year-1, 12, 1, 0, 0, 0 )
        pp.t2 = netcdftime.datetime( pp.t2.year, 3, 1, 0, 0, 0 )
        conditional_warning(scalar_coord(cm, 'time').bounds[0,0] != scalar_coord(cm, 'time').units.date2num(pp.t1), "modified t1 for climatological seasonal mean")
        conditional_warning(scalar_coord(cm, 'time').bounds[0,1] != scalar_coord(cm, 'time').units.date2num(pp.t2), "modified t2 for climatological seasonal mean")
        pp.lbft = scalar_coord(cm, 'forecast_period').units.convert(scalar_coord(cm, 'forecast_period').bounds[0, 1], 'hours')

    if \
            (scalar_coord(cm, 'time') is not None) and \
            (scalar_coord(cm, 'time').has_bounds()) and \
            (scalar_coord(cm, 'time').units.num2date(scalar_coord(cm, 'time').bounds[0,0]).year != scalar_coord(cm, 'time').units.num2date(scalar_coord(cm, 'time').bounds[0,1]).year) and \
            (scalar_coord(cm, 'forecast_period') is not None) and \
            (scalar_coord(cm, 'forecast_period').has_bounds()) and \
            (scalar_coord(cm, 'clim_season') is not None) and \
            ('clim_season' in cm.cell_methods[-1].coord_names) and \
            (scalar_coord(cm, 'clim_season').points[0] == 'mam'):
        pp.lbtim.ia = 0
        pp.lbtim.ib = 3
        pp.t1 = scalar_coord(cm, 'time').units.num2date(scalar_coord(cm, 'time').bounds[0,0])
        pp.t2 = scalar_coord(cm, 'time').units.num2date(scalar_coord(cm, 'time').bounds[0,1])
        pp.t1 = netcdftime.datetime( pp.t1.year, 3, 1, 0, 0, 0 )
        pp.t2 = netcdftime.datetime( pp.t2.year, 6, 1, 0, 0, 0 )
        conditional_warning(scalar_coord(cm, 'time').bounds[0,0] != scalar_coord(cm, 'time').units.date2num(pp.t1), "modified t1 for climatological seasonal mean")
        conditional_warning(scalar_coord(cm, 'time').bounds[0,1] != scalar_coord(cm, 'time').units.date2num(pp.t2), "modified t2 for climatological seasonal mean")
        pp.lbft = scalar_coord(cm, 'forecast_period').units.convert(scalar_coord(cm, 'forecast_period').bounds[0, 1], 'hours')

    if \
            (scalar_coord(cm, 'time') is not None) and \
            (scalar_coord(cm, 'time').has_bounds()) and \
            (scalar_coord(cm, 'time').units.num2date(scalar_coord(cm, 'time').bounds[0,0]).year != scalar_coord(cm, 'time').units.num2date(scalar_coord(cm, 'time').bounds[0,1]).year) and \
            (scalar_coord(cm, 'forecast_period') is not None) and \
            (scalar_coord(cm, 'forecast_period').has_bounds()) and \
            (scalar_coord(cm, 'clim_season') is not None) and \
            ('clim_season' in cm.cell_methods[-1].coord_names) and \
            (scalar_coord(cm, 'clim_season').points[0] == 'jja'):
        pp.lbtim.ia = 0
        pp.lbtim.ib = 3
        pp.t1 = scalar_coord(cm, 'time').units.num2date(scalar_coord(cm, 'time').bounds[0,0])
        pp.t2 = scalar_coord(cm, 'time').units.num2date(scalar_coord(cm, 'time').bounds[0,1])
        pp.t1 = netcdftime.datetime( pp.t1.year, 6, 1, 0, 0, 0 )
        pp.t2 = netcdftime.datetime( pp.t2.year, 9, 1, 0, 0, 0 )
        conditional_warning(scalar_coord(cm, 'time').bounds[0,0] != scalar_coord(cm, 'time').units.date2num(pp.t1), "modified t1 for climatological seasonal mean")
        conditional_warning(scalar_coord(cm, 'time').bounds[0,1] != scalar_coord(cm, 'time').units.date2num(pp.t2), "modified t2 for climatological seasonal mean")
        pp.lbft = scalar_coord(cm, 'forecast_period').units.convert(scalar_coord(cm, 'forecast_period').bounds[0, 1], 'hours')

    if \
            (scalar_coord(cm, 'time') is not None) and \
            (scalar_coord(cm, 'time').has_bounds()) and \
            (scalar_coord(cm, 'time').units.num2date(scalar_coord(cm, 'time').bounds[0,0]).year != scalar_coord(cm, 'time').units.num2date(scalar_coord(cm, 'time').bounds[0,1]).year) and \
            (scalar_coord(cm, 'forecast_period') is not None) and \
            (scalar_coord(cm, 'forecast_period').has_bounds()) and \
            (scalar_coord(cm, 'clim_season') is not None) and \
            ('clim_season' in cm.cell_methods[-1].coord_names) and \
            (scalar_coord(cm, 'clim_season').points[0] == 'son'):
        pp.lbtim.ia = 0
        pp.lbtim.ib = 3
        pp.t1 = scalar_coord(cm, 'time').units.num2date(scalar_coord(cm, 'time').bounds[0,0])
        pp.t2 = scalar_coord(cm, 'time').units.num2date(scalar_coord(cm, 'time').bounds[0,1])
        pp.t1 = netcdftime.datetime( pp.t1.year, 9, 1, 0, 0, 0 )
        pp.t2 = netcdftime.datetime( pp.t2.year, 12, 1, 0, 0, 0 )
        conditional_warning(scalar_coord(cm, 'time').bounds[0,0] != scalar_coord(cm, 'time').units.date2num(pp.t1), "modified t1 for climatological seasonal mean")
        conditional_warning(scalar_coord(cm, 'time').bounds[0,1] != scalar_coord(cm, 'time').units.date2num(pp.t2), "modified t2 for climatological seasonal mean")
        pp.lbft = scalar_coord(cm, 'forecast_period').units.convert(scalar_coord(cm, 'forecast_period').bounds[0, 1], 'hours')

    if \
            (scalar_coord(cm, 'time') is not None) and \
            (scalar_coord(cm, 'time').units.calendar == '360_day'):
        pp.lbtim.ic = 2

    if \
            (scalar_coord(cm, 'time') is not None) and \
            (scalar_coord(cm, 'time').units.calendar == 'gregorian'):
        pp.lbtim.ic = 1

    if \
            (scalar_coord(cm, 'time') is not None) and \
            (scalar_coord(cm, 'time').units.calendar == '365_day'):
        pp.lbtim.ic = 4

    if vector_coord(cm, 'longitude') and not is_regular(vector_coord(cm, 'longitude')):
        pp.bzx = 0
        pp.bdx = 0
        pp.lbnpt = vector_coord(cm, 'longitude').shape[0]
        pp.x = vector_coord(cm, 'longitude').points

    if vector_coord(cm, 'grid_longitude') and not is_regular(vector_coord(cm, 'grid_longitude')):
        pp.bzx = 0
        pp.bdx = 0
        pp.lbnpt = vector_coord(cm, 'grid_longitude').shape[0]
        pp.x = vector_coord(cm, 'grid_longitude').points

    if vector_coord(cm, 'latitude') and not is_regular(vector_coord(cm, 'latitude')):
        pp.bzy = 0
        pp.bdy = 0
        pp.lbrow = vector_coord(cm, 'latitude').shape[0]
        pp.y = vector_coord(cm, 'latitude').points

    if vector_coord(cm, 'grid_latitude') and not is_regular(vector_coord(cm, 'grid_latitude')):
        pp.bzy = 0
        pp.bdy = 0
        pp.lbrow = vector_coord(cm, 'grid_latitude').shape[0]
        pp.y = vector_coord(cm, 'grid_latitude').points

    if vector_coord(cm, 'longitude') and is_regular(vector_coord(cm, 'longitude')):
        pp.bzx = vector_coord(cm, 'longitude').points[0] - regular_step(vector_coord(cm, 'longitude'))
        pp.bdx = regular_step(vector_coord(cm, 'longitude'))
        pp.lbnpt = len(vector_coord(cm, 'longitude').points)

    if vector_coord(cm, 'grid_longitude') and is_regular(vector_coord(cm, 'grid_longitude')):
        pp.bzx = vector_coord(cm, 'grid_longitude').points[0] - regular_step(vector_coord(cm, 'grid_longitude'))
        pp.bdx = regular_step(vector_coord(cm, 'grid_longitude'))
        pp.lbnpt = len(vector_coord(cm, 'grid_longitude').points)

    if vector_coord(cm, 'latitude') and is_regular(vector_coord(cm, 'latitude')):
        pp.bzy = vector_coord(cm, 'latitude').points[0] - regular_step(vector_coord(cm, 'latitude'))
        pp.bdy = regular_step(vector_coord(cm, 'latitude'))
        pp.lbrow = len(vector_coord(cm, 'latitude').points)

    if vector_coord(cm, 'grid_latitude') and is_regular(vector_coord(cm, 'grid_latitude')):
        pp.bzy = vector_coord(cm, 'grid_latitude').points[0] - regular_step(vector_coord(cm, 'grid_latitude'))
        pp.bdy = regular_step(vector_coord(cm, 'grid_latitude'))
        pp.lbrow = len(vector_coord(cm, 'grid_latitude').points)

    if cm.coord_system("RotatedGeogCS") is not None:
        pp.lbcode = int(pp.lbcode) + 100

    if \
            (vector_coord(cm, 'longitude') is not None) and \
            (vector_coord(cm, 'longitude').circular):
        pp.lbhem = 0

    if \
            (vector_coord(cm, 'grid_longitude') is not None) and \
            (vector_coord(cm, 'grid_longitude').circular):
        pp.lbhem = 0

    if \
            (vector_coord(cm, 'longitude') is not None) and \
            (not vector_coord(cm, 'longitude').circular):
        pp.lbhem = 3

    if \
            (vector_coord(cm, 'grid_longitude') is not None) and \
            (not vector_coord(cm, 'grid_longitude').circular):
        pp.lbhem = 3

    if \
            (vector_coord(cm, 'air_pressure') is not None) and \
            (not vector_coord(cm, 'air_pressure').circular) and \
            (vector_coord(cm, 'air_pressure').has_bounds()) and \
            (vector_coord(cm, 'latitude') is not None) and \
            (not vector_coord(cm, 'latitude').circular) and \
            (vector_coord(cm, 'latitude').has_bounds()):
        pp.lbcode = 10000 + int(100*10) + 1
        pp.bgor = 0
        pp.y = vector_coord(cm, 'air_pressure').points
        pp.y_lower_bound = vector_coord(cm, 'air_pressure').bounds[:,0]
        pp.y_upper_bound = vector_coord(cm, 'air_pressure').bounds[:,1]
        pp.x = vector_coord(cm, 'latitude').points
        pp.x_lower_bound = vector_coord(cm, 'latitude').bounds[:,0]
        pp.x_upper_bound = vector_coord(cm, 'latitude').bounds[:,1]
        pp.lbrow = vector_coord(cm, 'air_pressure').shape[0]
        pp.lbnpt = vector_coord(cm, 'latitude').shape[0]
        pp.bzx = pp.bzy = pp.bdx = pp.bdy = 0

    if \
            (vector_coord(cm, 'depth') is not None) and \
            (not vector_coord(cm, 'depth').circular) and \
            (vector_coord(cm, 'depth').has_bounds()) and \
            (vector_coord(cm, 'latitude') is not None) and \
            (not vector_coord(cm, 'latitude').circular) and \
            (vector_coord(cm, 'latitude').has_bounds()):
        pp.lbcode = 10000 + int(100*10) + 4
        pp.bgor = 0
        pp.y = vector_coord(cm, 'depth').points
        pp.y_lower_bound = vector_coord(cm, 'depth').bounds[:,0]
        pp.y_upper_bound = vector_coord(cm, 'depth').bounds[:,1]
        pp.x = vector_coord(cm, 'latitude').points
        pp.x_lower_bound = vector_coord(cm, 'latitude').bounds[:,0]
        pp.x_upper_bound = vector_coord(cm, 'latitude').bounds[:,1]
        pp.lbrow = vector_coord(cm, 'depth').shape[0]
        pp.lbnpt = vector_coord(cm, 'latitude').shape[0]
        pp.bzx = pp.bzy = pp.bdx = pp.bdy = 0

    if \
            (vector_coord(cm, 'eta') is not None) and \
            (not vector_coord(cm, 'eta').circular) and \
            (vector_coord(cm, 'eta').has_bounds()) and \
            (vector_coord(cm, 'latitude') is not None) and \
            (not vector_coord(cm, 'latitude').circular) and \
            (vector_coord(cm, 'latitude').has_bounds()):
        pp.lbcode = 10000 + int(100*10) + 3
        pp.bgor = 0
        pp.y = vector_coord(cm, 'eta').points
        pp.y_lower_bound = vector_coord(cm, 'eta').bounds[:,0]
        pp.y_upper_bound = vector_coord(cm, 'eta').bounds[:,1]
        pp.x = vector_coord(cm, 'latitude').points
        pp.x_lower_bound = vector_coord(cm, 'latitude').bounds[:,0]
        pp.x_upper_bound = vector_coord(cm, 'latitude').bounds[:,1]
        pp.lbrow = vector_coord(cm, 'eta').shape[0]
        pp.lbnpt = vector_coord(cm, 'latitude').shape[0]
        pp.bzx = pp.bzy = pp.bdx = pp.bdy = 0

    if \
            (vector_coord(cm, 'depth') is not None) and \
            (not vector_coord(cm, 'depth').circular) and \
            (vector_coord(cm, 'depth').has_bounds()) and \
            (vector_coord(cm, 'time') is not None) and \
            (not vector_coord(cm, 'time').circular) and \
            (vector_coord(cm, 'time').has_bounds()):
        pp.lbcode = 10000 + int(100*23) + 4
        pp.bgor = 0
        pp.y = vector_coord(cm, 'depth').points
        pp.y_lower_bound = vector_coord(cm, 'depth').bounds[:,0]
        pp.y_upper_bound = vector_coord(cm, 'depth').bounds[:,1]
        pp.x = vector_coord(cm, 'time').points
        pp.x_lower_bound = vector_coord(cm, 'time').bounds[:,0]
        pp.x_upper_bound = vector_coord(cm, 'time').bounds[:,1]
        pp.lbrow = vector_coord(cm, 'depth').shape[0]
        pp.lbnpt = vector_coord(cm, 'time').shape[0]
        pp.bzx = pp.bzy = pp.bdx = pp.bdy = 0

    if \
            (vector_coord(cm, 'air_pressure') is not None) and \
            (not vector_coord(cm, 'air_pressure').circular) and \
            (vector_coord(cm, 'air_pressure').has_bounds()) and \
            (vector_coord(cm, 'time') is not None) and \
            (not vector_coord(cm, 'time').circular) and \
            (vector_coord(cm, 'time').has_bounds()):
        pp.lbcode = 10000 + int(100*23) + 1
        pp.bgor = 0
        pp.y = vector_coord(cm, 'air_pressure').points
        pp.y_lower_bound = vector_coord(cm, 'air_pressure').bounds[:,0]
        pp.y_upper_bound = vector_coord(cm, 'air_pressure').bounds[:,1]
        pp.x = vector_coord(cm, 'time').points
        pp.x_lower_bound = vector_coord(cm, 'time').bounds[:,0]
        pp.x_upper_bound = vector_coord(cm, 'time').bounds[:,1]
        pp.lbrow = vector_coord(cm, 'air_pressure').shape[0]
        pp.lbnpt = vector_coord(cm, 'time').shape[0]
        pp.bzx = pp.bzy = pp.bdx = pp.bdy = 0

    if cm.attributes.get("ukmo__process_flags", None):
        pp.lbproc += sum([iris.fileformats.pp.lbproc_map[name] for name in cm.attributes["ukmo__process_flags"]])

    if scalar_cell_method(cm, 'mean', 'time') is not None:
        pp.lbproc += 128

    if scalar_cell_method(cm, 'maximum', 'time') is not None:
        pp.lbproc += 8192

    if \
            (scalar_coord(cm, 'pseudo_level') is not None) and \
            (not scalar_coord(cm, 'pseudo_level').bounds):
        pp.lbuser[4] = scalar_coord(cm, 'pseudo_level').points[0]

    if \
            (scalar_coord(cm, 'height') is not None) and \
            (not scalar_coord(cm, 'height').bounds) and \
            (scalar_coord(cm, 'height').points[0] == 1.5) and \
            (cm.name() == 'air_temperature'):
        pp.lbvc = 129
        pp.blev = -1

    if \
            (pp.lbvc == 0) and \
            (scalar_coord(cm, 'height') is not None) and \
            (not scalar_coord(cm, 'height').bounds):
        pp.lbvc = 1
        pp.blev = cm.coord('height').points[0]

    if \
            (scalar_coord(cm, 'air_pressure') is not None) and \
            (not scalar_coord(cm, 'air_pressure').bounds):
        pp.lbvc = 8
        pp.blev = scalar_coord(cm, 'air_pressure').points[0]

    if \
            (scalar_coord(cm, 'pressure') is not None) and \
            (not scalar_coord(cm, 'pressure').bounds):
        pp.lbvc = 8
        pp.blev = scalar_coord(cm, 'pressure').points[0]

    if \
            (scalar_coord(cm, 'model_level_number') is not None) and \
            (not scalar_coord(cm, 'model_level_number').bounds) and \
            (scalar_coord(cm, 'depth') is not None) and \
            (not scalar_coord(cm, 'depth').bounds):
        pp.lbvc = 2
        pp.lblev = scalar_coord(cm, 'model_level_number').points[0]
        pp.blev = scalar_coord(cm, 'depth').points[0]

    if \
            (scalar_coord(cm, 'soil_model_level_number') is not None) and \
            (not scalar_coord(cm, 'soil_model_level_number').bounds) and \
            (scalar_coord(cm, 'air_pressure') is None) and \
            (scalar_coord(cm, 'depth') is None) and \
            (scalar_coord(cm, 'height') is None) and \
            (scalar_coord(cm, 'pressure') is None) and \
            (cm.standard_name is not None) and \
            ('soil' in cm.standard_name):
        pp.lbvc = 6
        pp.lblev = scalar_coord(cm, 'soil_model_level_number').points[0]
        pp.blev = pp.lblev

    if \
            (scalar_coord(cm, 'air_potential_temperature') is not None) and \
            (not scalar_coord(cm, 'air_potential_temperature').bounds) and \
            (scalar_coord(cm, 'air_pressure') is None) and \
            (scalar_coord(cm, 'depth') is None) and \
            (scalar_coord(cm, 'height') is None) and \
            (scalar_coord(cm, 'pressure') is None) and \
            (scalar_coord(cm, 'model_level_number') is None):
        pp.lbvc = 19
        pp.lblev = scalar_coord(cm, 'air_potential_temperature').points[0]
        pp.blev = scalar_coord(cm, 'air_potential_temperature').points[0]

    if \
            (not has_aux_factory(cm, iris.aux_factory.HybridHeightFactory)) and \
            (scalar_coord(cm, 'model_level_number') is not None) and \
            (scalar_coord(cm, 'model_level_number').bounds is None) and \
            (scalar_coord(cm, 'level_height') is not None) and \
            (scalar_coord(cm, 'level_height').bounds is not None) and \
            (scalar_coord(cm, 'sigma') is not None) and \
            (scalar_coord(cm, 'sigma').bounds is not None):
        pp.lbvc = 65
        pp.lblev = scalar_coord(cm, 'model_level_number').points[0]
        pp.blev = scalar_coord(cm, 'level_height').points[0]
        pp.brlev = scalar_coord(cm, 'level_height').bounds[0, 0]
        pp.brsvd[0] = scalar_coord(cm, 'level_height').bounds[0, 1]
        pp.bhlev = scalar_coord(cm, 'sigma').points[0]
        pp.bhrlev = scalar_coord(cm, 'sigma').bounds[0, 0]
        pp.brsvd[1] = scalar_coord(cm, 'sigma').bounds[0, 1]

    if \
            (has_aux_factory(cm, iris.aux_factory.HybridHeightFactory)) and \
            (scalar_coord(cm, 'model_level_number') is not None) and \
            (scalar_coord(cm, 'model_level_number').bounds is None) and \
            (aux_factory(cm, iris.aux_factory.HybridHeightFactory).dependencies['delta'] is not None) and \
            (aux_factory(cm, iris.aux_factory.HybridHeightFactory).dependencies['delta'].bounds is not None) and \
            (aux_factory(cm, iris.aux_factory.HybridHeightFactory).dependencies['sigma'] is not None) and \
            (aux_factory(cm, iris.aux_factory.HybridHeightFactory).dependencies['sigma'].bounds is not None):
        pp.lbvc = 65
        pp.lblev = scalar_coord(cm, 'model_level_number').points[0]
        pp.blev = aux_factory(cm, iris.aux_factory.HybridHeightFactory).dependencies['delta'].points[0]
        pp.brlev = aux_factory(cm, iris.aux_factory.HybridHeightFactory).dependencies['delta'].bounds[0, 0]
        pp.brsvd[0] = aux_factory(cm, iris.aux_factory.HybridHeightFactory).dependencies['delta'].bounds[0, 1]
        pp.bhlev = aux_factory(cm, iris.aux_factory.HybridHeightFactory).dependencies['sigma'].points[0]
        pp.bhrlev = aux_factory(cm, iris.aux_factory.HybridHeightFactory).dependencies['sigma'].bounds[0, 0]
        pp.brsvd[1] = aux_factory(cm, iris.aux_factory.HybridHeightFactory).dependencies['sigma'].bounds[0, 1]

    if \
            (has_aux_factory(cm, iris.aux_factory.HybridPressureFactory)) and \
            (scalar_coord(cm, 'model_level_number') is not None) and \
            (scalar_coord(cm, 'model_level_number').bounds is None) and \
            (aux_factory(cm, iris.aux_factory.HybridPressureFactory).dependencies['delta'] is not None) and \
            (aux_factory(cm, iris.aux_factory.HybridPressureFactory).dependencies['delta'].bounds is not None) and \
            (aux_factory(cm, iris.aux_factory.HybridPressureFactory).dependencies['sigma'] is not None) and \
            (aux_factory(cm, iris.aux_factory.HybridPressureFactory).dependencies['sigma'].bounds is not None):
        pp.lbvc = 9
        pp.lblev = scalar_coord(cm, 'model_level_number').points[0]
        pp.blev = aux_factory(cm, iris.aux_factory.HybridPressureFactory).dependencies['sigma'].points[0]
        pp.brlev = aux_factory(cm, iris.aux_factory.HybridPressureFactory).dependencies['sigma'].bounds[0, 0]
        pp.brsvd[0] = aux_factory(cm, iris.aux_factory.HybridPressureFactory).dependencies['sigma'].bounds[0, 1]
        pp.bhlev = aux_factory(cm, iris.aux_factory.HybridPressureFactory).dependencies['delta'].points[0]
        pp.bhrlev = aux_factory(cm, iris.aux_factory.HybridPressureFactory).dependencies['delta'].bounds[0, 0]
        pp.brsvd[1] = aux_factory(cm, iris.aux_factory.HybridPressureFactory).dependencies['delta'].bounds[0, 1]

    if isinstance(cm.data, ma.core.MaskedArray):
        pp.bmdi = cm.data.fill_value

    if not isinstance(cm.data, ma.core.MaskedArray):
        pp.bmdi = -1e30

    if (cm.standard_name, cm.long_name, str(cm.units)) in iris.fileformats.um_cf_map.CF_TO_LBFC:
        pp.lbfc = iris.fileformats.um_cf_map.CF_TO_LBFC[(cm.standard_name, cm.long_name, str(cm.units))]

    if \
            ('STASH' in cm.attributes) and \
            (str(cm.attributes['STASH']) in iris.fileformats._ff_cross_references.STASH_TRANS):
        pp.lbfc = iris.fileformats._ff_cross_references.STASH_TRANS[str(cm.attributes['STASH'])].field_code

    return (factories, references, standard_name, long_name, units, attributes,
            cell_methods, dim_coords_and_dims, aux_coords_and_dims)
