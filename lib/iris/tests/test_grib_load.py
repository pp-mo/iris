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

# Import iris tests first so that some things can be initialised before
# importing anything else
import iris.tests as tests

import datetime
import os

import numpy as np
import matplotlib.pyplot as plt
import gribapi
import mock

import iris
import iris.fileformats.grib
import iris.plot as iplt
import iris.util
import iris.tests.stock


# Construct a mock object to mimic the gribapi for GribWrapper testing.
_mock_gribapi = mock.Mock(spec=gribapi)
_mock_gribapi.GribInternalError = Exception


def _mock_gribapi_fetch(message, key):
    """
    Fake the gribapi key-fetch.

    Fetch key-value from the fake message (dictionary).
    If the key is not present, raise the diagnostic exception.

    """
    if key in message.keys():
        return message[key]
    else:
        raise _mock_gribapi.GribInternalError


def _mock_gribapi__grib_is_missing(grib_message, keyname):
    """
    Fake the gribapi key-existence enquiry.

    Return whether the key exists in the fake message (dictionary).

    """
    return (keyname not in grib_message)


def _mock_gribapi__grib_get_native_type(grib_message, keyname):
    """
    Fake the gribapi type-discovery operation.

    Return type of key-value in the fake message (dictionary).
    If the key is not present, raise the diagnostic exception.

    """
    if keyname in grib_message:
        return type(grib_message[keyname])
    raise _mock_gribapi.GribInternalError(keyname)

_mock_gribapi.grib_get_long = mock.Mock(side_effect=_mock_gribapi_fetch)
_mock_gribapi.grib_get_string = mock.Mock(side_effect=_mock_gribapi_fetch)
_mock_gribapi.grib_get_double = mock.Mock(side_effect=_mock_gribapi_fetch)
_mock_gribapi.grib_get_double_array = mock.Mock(
    side_effect=_mock_gribapi_fetch)
_mock_gribapi.grib_is_missing = mock.Mock(
    side_effect=_mock_gribapi__grib_is_missing)
_mock_gribapi.grib_get_native_type = mock.Mock(
    side_effect=_mock_gribapi__grib_get_native_type)


@iris.tests.skip_data
class TestGribLoad(tests.GraphicsTest):
  
    def test_load(self):
                
        cubes = iris.load(tests.get_data_path(('GRIB', 'rotated_uk', "uk_wrongparam.grib1")))
        self.assertCML(cubes, ("grib_load", "rotated.cml"))
        
        cubes = iris.load(tests.get_data_path(('GRIB', "time_processed", "time_bound.grib1")))
        self.assertCML(cubes, ("grib_load", "time_bound_grib1.cml"))

        cubes = iris.load(tests.get_data_path(('GRIB', "time_processed", "time_bound.grib2")))
        self.assertCML(cubes, ("grib_load", "time_bound_grib2.cml"))
        
        cubes = iris.load(tests.get_data_path(('GRIB', "3_layer_viz", "3_layer.grib2")))
        cubes = iris.cube.CubeList([cubes[1], cubes[0], cubes[2]])
        self.assertCML(cubes, ("grib_load", "3_layer.cml"))
        
    def test_y_fastest(self):
        cubes = iris.load(tests.get_data_path(("GRIB", "y_fastest", "y_fast.grib2")))
        self.assertCML(cubes, ("grib_load", "y_fastest.cml"))
        iplt.contourf(cubes[0])
        plt.gca().coastlines()
        plt.title("y changes fastest")
        self.check_graphic()

    def test_ij_directions(self):
        
        def old_compat_load(name):
            cube = iris.load(tests.get_data_path(('GRIB', 'ij_directions', name)))[0]
            return [cube]
        
        cubes = old_compat_load("ipos_jpos.grib2")
        self.assertCML(cubes, ("grib_load", "ipos_jpos.cml"))
        iplt.contourf(cubes[0])
        plt.gca().coastlines()
        plt.title("ipos_jpos cube")
        self.check_graphic()

        cubes = old_compat_load("ipos_jneg.grib2")
        self.assertCML(cubes, ("grib_load", "ipos_jneg.cml"))
        iplt.contourf(cubes[0])
        plt.gca().coastlines()
        plt.title("ipos_jneg cube")
        self.check_graphic()

        cubes = old_compat_load("ineg_jneg.grib2")
        self.assertCML(cubes, ("grib_load", "ineg_jneg.cml"))
        iplt.contourf(cubes[0])
        plt.gca().coastlines()
        plt.title("ineg_jneg cube")
        self.check_graphic()

        cubes = old_compat_load("ineg_jpos.grib2")
        self.assertCML(cubes, ("grib_load", "ineg_jpos.cml"))
        iplt.contourf(cubes[0])
        plt.gca().coastlines()
        plt.title("ineg_jpos cube")
        self.check_graphic()
        
    def test_shape_of_earth(self):
        
        def old_compat_load(name):
            cube = iris.load(tests.get_data_path(('GRIB', 'shape_of_earth', name)))[0]
            return cube
        
        #pre-defined sphere
        cube = old_compat_load("0.grib2")
        self.assertCML(cube, ("grib_load", "earth_shape_0.cml"))

        #custom sphere
        cube = old_compat_load("1.grib2")
        self.assertCML(cube, ("grib_load", "earth_shape_1.cml"))

        #IAU65 oblate sphere 
        cube = old_compat_load("2.grib2")
        self.assertCML(cube, ("grib_load", "earth_shape_2.cml"))

        #custom oblate spheroid (km) 
        cube = old_compat_load("3.grib2")
        self.assertCML(cube, ("grib_load", "earth_shape_3.cml"))

        #IAG-GRS80 oblate spheroid 
        cube = old_compat_load("4.grib2")
        self.assertCML(cube, ("grib_load", "earth_shape_4.cml"))

        #WGS84
        cube = old_compat_load("5.grib2")
        self.assertCML(cube, ("grib_load", "earth_shape_5.cml"))

        #pre-defined sphere
        cube = old_compat_load("6.grib2")
        self.assertCML(cube, ("grib_load", "earth_shape_6.cml"))

        #custom oblate spheroid (m)
        cube = old_compat_load("7.grib2")
        self.assertCML(cube, ("grib_load", "earth_shape_7.cml"))

        #grib1 - same as grib2 shape 6, above
        cube = old_compat_load("global.grib1")
        self.assertCML(cube, ("grib_load", "earth_shape_grib1.cml"))

    def test_custom_rules(self):
        # Test custom rule evaluation.
        # Default behaviour
#        data_path = tests.get_data_path(('GRIB', 'global_t', 'global.grib2'))
#        cube = iris.load_cube(data_path)
        cube = tests.stock.global_grib2()
        self.assertEqual(cube.name(), 'air_temperature')

        # Custom behaviour
        temp_path = iris.util.create_temp_filename()
        f = open(temp_path, 'w')
        f.write('\n'.join((
            'IF',
            'grib.edition == 2',
            'grib.discipline == 0',
            'grib.parameterCategory == 0',
            'grib.parameterNumber == 0',
            'THEN',
            'CMAttribute("long_name", "customised")',
            'CMAttribute("standard_name", None)')))
        f.close()
        iris.fileformats.grib.add_load_rules(temp_path)
        cube = tests.stock.global_grib2()
        self.assertEqual(cube.name(), 'customised')
        os.remove(temp_path)
        
        # Back to default
        iris.fileformats.grib.reset_load_rules()
        cube = tests.stock.global_grib2()
        self.assertEqual(cube.name(), 'air_temperature')
        
    def test_fp_units(self):
        # Test different units for forecast period (just ones we care about)

        # Define basic 'fake message' contents, for testing underlying methods.
        # These contain just the minimum keys needed to create a GribWrapper.

        # edition-1 test message data ...
        fake_message_ed1 = {
            'Ni': 1,
            'Nj': 1,
            'edition': 1,
            'alternativeRowScanning': 0,
            'startStep': 24,
            'centre': 'ecmf',
            'year': 2007,
            'month': 3,
            'day': 23,
            'hour': 12,
            'minute': 0,
            'timeRangeIndicator': 0,
            'P1': 2, 'P2': 0,
            # time units : must set both of these
            'unitOfTime': None,
            'indicatorOfUnitOfTimeRange': None,
            'shapeOfTheEarth': 6,
            'gridType': 'rotated_ll',
            'angleOfRotation': 0.0,
            'iDirectionIncrementInDegrees': 0.036,
            'jDirectionIncrementInDegrees': 0.036,
            'iScansNegatively': 0,
            'jScansPositively': 1,
            'longitudeOfFirstGridPointInDegrees': -5.70,
            'latitudeOfFirstGridPointInDegrees': -4.452,
            'jPointsAreConsecutive': 0,
            'values': np.array([[1.0]]),
        }
        # edition-2 test message data ...
        fake_message_ed2 = {
            'Ni': 1,
            'Nj': 1,
            'edition': 2,
            'alternativeRowScanning': 0,
            'iDirectionIncrementGiven': 1,
            'jDirectionIncrementGiven': 1,
            'uvRelativeToGrid': 0,
            'forecastTime': 24,
            'centre': 'ecmf',
            'year': 2007,
            'month': 3,
            'day': 23,
            'hour': 12,
            'minute': 0,
            'productDefinitionTemplateNumber': 0,
            'stepRange': 24,
            'shapeOfTheEarth': 6,
            'gridType': 'rotated_ll',
            'angleOfRotation': 0.0,
            # time units : must be set
            'indicatorOfUnitOfTimeRange': None,
            'iDirectionIncrementInDegrees': 0.036,
            'jDirectionIncrementInDegrees': 0.036,
            'iScansNegatively': 0,
            'jScansPositively': 1,
            'longitudeOfFirstGridPointInDegrees': -5.70,
            'latitudeOfFirstGridPointInDegrees': -4.452,
            'jPointsAreConsecutive': 0,
            'values': np.array([[1.0]]),
        }

        # Make a list of testcases for various time-units and grib-editions.
        # Format: (edition, code, unit-equivalent-seconds, description-string).
        hour_secs = 3600.0
        test_set = (
            (1, 0, 60.0, 'minutes'),
            (1, 1, hour_secs, 'hours'),
            (1, 2, 24.0 * hour_secs, 'days'),
            (1, 10, 3.0 * hour_secs, '3 hours'),
            (1, 11, 6.0 * hour_secs, '6 hours'),
            (1, 12, 12.0 * hour_secs, '12 hours'),
            (1, 13, 0.25 * hour_secs, '15 minutes'),
            (1, 14, 0.5 * hour_secs, '30 minutes'),
            (1, 254, 1.0, 'seconds'),
            (2, 0, 60.0, 'minutes'),
            (2, 1, hour_secs, 'hours'),
            (2, 2, 24.0 * hour_secs, 'days'),
            (2, 13, 1.0, 'seconds'),
            (2, 10, 3.0 * hour_secs, '3 hours'),
            (2, 11, 6.0 * hour_secs, '6 hours'),
            (2, 12, 12.0 * hour_secs, '12 hours'),
        )

        # Check the unit-handling for each supported units-code and edition.
        with mock.patch('iris.fileformats.grib.gribapi', _mock_gribapi):
            for test_controls in test_set:
                (
                    grib_edition, timeunit_codenum,
                    timeunit_secs, timeunit_str
                ) = test_controls
                assert grib_edition in (1, 2)

                # Select the grib-1 or grib-2 basic test message.
                if grib_edition == 1:
                    fake_message = fake_message_ed1
                elif grib_edition == 2:
                    fake_message = fake_message_ed2

                # Set the timeunit in the message.
                fake_message['indicatorOfUnitOfTimeRange'] = timeunit_codenum
                if grib_edition == 1:
                    # for some odd reason, GRIB1 code uses *both* of these
                    # NOTE kludge -- the 2 keys are really the same thing
                    fake_message['unitOfTime'] = timeunit_codenum

                # Make a GribWrapper object to test.
                wrapped_msg = iris.fileformats.grib.GribWrapper(fake_message)

                # Check the units string.
                forecast_timeunit = wrapped_msg._forecastTimeUnit
                self.assertEqual(
                    forecast_timeunit, timeunit_str,
                    'Bad unit string for edition={ed:01d}, '
                    'unitcode={code:01d} : '
                    'expected="{wanted}" GOT="{got}"'.format(
                        ed=grib_edition,
                        code=timeunit_codenum,
                        wanted=timeunit_str,
                        got=forecast_timeunit
                    )
                )

                # Check the data-starttime calculation.
                interval_start_to_end = (
                    wrapped_msg._phenomenonDateTime
                    - wrapped_msg._referenceDateTime
                )
                if grib_edition == 1:
                    interval_from_units = wrapped_msg.P1
                else:
                    interval_from_units = wrapped_msg.forecastTime
                interval_from_units *= datetime.timedelta(0, timeunit_secs)
                self.assertEqual(
                    interval_start_to_end, interval_from_units,
                    'Inconsistent start time offset for edition={ed:01d}, '
                    'unitcode={code:01d} : '
                    'from-unit="{unit_str}" '
                    'from-phenom-minus-ref="{e2e_str}"'.format(
                        ed=grib_edition,
                        code=timeunit_codenum,
                        unit_str=interval_from_units,
                        e2e_str=interval_start_to_end
                    )
                )


if __name__ == "__main__":
    tests.main()
    print "finished"
