# (C) British Crown Copyright 2013, Met Office
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
import iris.tests as tests

#import matplotlib as mpl
#import matplotlib.pyplot as plt
#plt.switch_backend('tkagg')
#import iris.plot as iplt

import mock
import numpy as np

import cartopy.crs as ccrs
import iris
from iris.analysis.cartography import unrotate_pole
from iris.experimental.shapefiles import export_shapefiles
import iris.tests.stock as istk

do_make_real_files = True

class Test_export_shapefiles(tests.IrisTest):
    def setUp(self):
        # Make a small sample cube.
        cube = istk.simple_pp()
        cube = cube[::10, ::10]
        cube = cube[1:5, 1:4]
        self.simple_latlon_cube = cube

    def test_basic_unrotated(self):
        # Save a simple 2d cube
        cube = self.simple_latlon_cube

        if do_make_real_files:
            out_filepath = ('/net/home/h05/itpp/Iris/sprints/'
                            '20131028_new-agile_and_shapefiles/'
                            'scit322_shapefiles_geotiff/tmp_out/test_plain')
            export_shapefiles(cube, out_filepath)

        mock_shapefile_module = mock.Mock(spec=['Writer', 'POINT'])
        mock_shapefile_writer = mock.Mock(
            spec=['field', 'record', 'point', 'save'])
        mock_shapefile_module.Writer = mock.Mock(
            return_value=mock_shapefile_writer)
        test_filepath = 'an/arbitrary/file_path'
        mock_file_open_method = mock.mock_open()
        with mock.patch('iris.experimental.shapefiles.shapefile',
                        mock_shapefile_module):
            with mock.patch('iris.experimental.shapefiles.open',
                            mock_file_open_method,
                            create=True):
                export_shapefiles(cube, test_filepath)

        # Behavioural testing ...
        # Module has been called just once, to make a 'Writer'
        self.assertEqual(len(mock_shapefile_module.mock_calls), 1)
        self.assertEqual(mock_shapefile_module.mock_calls[0][0], 'Writer')
        # writer.field has been called once with record keys = ['data_value']
        self.assertEqual(len(mock_shapefile_writer.field.mock_calls), 1)
        self.assertEqual(mock_shapefile_writer.field.mock_calls[0][1],
                         ('data_value',))
        # last writer call was to 'save'
        self.assertEqual(mock_shapefile_writer.mock_calls[-1][0], 'save')
        # last writer call had filepath as single argument
        self.assertEqual(mock_shapefile_writer.mock_calls[-1][1],
                         (test_filepath,))

        # pull out x/y/data values from the calls to writer.point
        x_vals = [mock_call[1][0]
                  for mock_call in mock_shapefile_writer.mock_calls
                  if mock_call[0] == 'point']
        y_vals = [mock_call[1][1]
                  for mock_call in mock_shapefile_writer.mock_calls
                  if mock_call[0] == 'point']
        data_vals = [mock_call[1][0]
                     for mock_call in mock_shapefile_writer.mock_calls
                     if mock_call[0] == 'record']

        # Check values as expected
        self.assertArrayAllClose(np.array(x_vals)[[0, 4, 8]],
                                 cube.coord('longitude').points)
        self.assertArrayAllClose(np.array(y_vals)[[0, 3, 6, 9]],
                                 cube.coord('latitude').points)
        self.assertArrayAllClose(data_vals, cube.data.flat)

        # Check that a projection file was opened.
        self.assertEqual(mock_file_open_method.mock_calls[0][1][0],
                         test_filepath + '.prj')
        # Check __enter__ and __exit__ were called, and suitable text written.
        open_file_mock = mock_file_open_method()
        self.assertEqual(len(open_file_mock.__enter__.mock_calls), 1)
        self.assertEqual(open_file_mock.write.mock_calls[0][1][0][:7],
                         'GEOGCS[')
        self.assertEqual(len(open_file_mock.__exit__.mock_calls), 1)

#        # Plot results
#        iplt.pcolormesh(cube)
#        plt.gca().coastlines()
#        print
#        print 'top left :', ccrs.Geodetic().transform_point(
#            cube.coord(axis='X').points[0],
#            cube.coord(axis='Y').points[0],
#            cube.coord(axis='X').coord_system.as_cartopy_crs()
#            )
#        print 'bottom right :', ccrs.Geodetic().transform_point(
#            cube.coord(axis='X').points[-1],
#            cube.coord(axis='Y').points[-1],
#            cube.coord(axis='X').coord_system.as_cartopy_crs()
#            )
#        print cube.data
#        plt.show()

    def test_rotated(self):
        cube = self.simple_latlon_cube
        # Modify this cube to give it a rotated projection.
        grid_lat = 73.2
        grid_lon = 137.4
        cs_rot = iris.coord_systems.RotatedGeogCS(
            grid_north_pole_latitude=grid_lat,
            grid_north_pole_longitude=grid_lon)
        x_coord = cube.coord(axis='x')
        y_coord = cube.coord(axis='y')
        x_coord.rename('grid_longitude')
        x_coord.coord_system = cs_rot
        y_coord.rename('grid_latitude')
        y_coord.coord_system = cs_rot

        if do_make_real_files:
            out_filepath = ('/net/home/h05/itpp/Iris/sprints/'
                            '20131028_new-agile_and_shapefiles/'
                            'scit322_shapefiles_geotiff/tmp_out/test_rot')
            export_shapefiles(cube, out_filepath)

        mock_shapefile_module = mock.Mock(spec=['Writer', 'POINT'])
        mock_shapefile_writer = mock.Mock(
            spec=['field', 'record', 'point', 'save'])
        mock_shapefile_module.Writer = mock.Mock(
            return_value=mock_shapefile_writer)
        test_filepath = 'an/arbitrary/file_path'
        with mock.patch('iris.experimental.shapefiles.shapefile',
                        mock_shapefile_module):
            with mock.patch('iris.experimental.shapefiles.open',
                            mock.mock_open(),
                            create=True):
                export_shapefiles(cube, test_filepath)

        # pull out x/y/data values from the calls to writer.point
        x_vals = [mock_call[1][0]
                  for mock_call in mock_shapefile_writer.mock_calls
                  if mock_call[0] == 'point']
        y_vals = [mock_call[1][1]
                  for mock_call in mock_shapefile_writer.mock_calls
                  if mock_call[0] == 'point']
        data_vals = [mock_call[1][0]
                     for mock_call in mock_shapefile_writer.mock_calls
                     if mock_call[0] == 'record']

        # Check coordinate values against an independent rotation calculation.
        grid_x_points, grid_y_points = np.meshgrid(x_coord.points,
                                                   y_coord.points)
        true_x_points, true_y_points = unrotate_pole(
            rotated_lons=grid_x_points,
            rotated_lats=grid_y_points,
            pole_lon=grid_lon, pole_lat=grid_lat)
        self.assertArrayAllClose(x_vals, true_x_points.flat)
        self.assertArrayAllClose(y_vals, true_y_points.flat)
        # Check data values as original.
        self.assertArrayAllClose(data_vals, cube.data.flat)


if __name__ == "__main__":
    tests.main()
