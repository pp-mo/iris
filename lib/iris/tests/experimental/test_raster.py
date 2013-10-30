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
import PIL.Image

import cartopy.crs as ccrs
import iris
from iris.experimental.raster import export_geotiff
from iris.experimental.shapefiles import export_shapefile
import iris.tests.stock as istk


@tests.skip_data
class Test_export_geotiff(tests.GraphicsTest):
    def check_tiff_header(self, geotiff_fh, reference_filename):
        """
        Checks the given tiff file handle's metadata matches the
        reference file contents.

        """
        im = PIL.Image.open(geotiff_fh)
        tiff_header = '\n'.join(str((tag, val))
                                for tag, val in sorted(im.tag.items()))

        reference_path = tests.get_result_path(reference_filename)

        self._check_same(tiff_header, reference_path, reference_filename,
                         type_comparison_name='Tiff header')

    def check_tiff(self, cube, tif_header):
        with self.temp_filename('.tif') as temp_filename:
            export_geotiff(cube, temp_filename)

            # Check the metadata is correct.
            with open(temp_filename) as fh:
                self.check_tiff_header(fh, ('experimental', 'raster',
                                            tif_header))

            # Ensure that north is at the top then check the data is correct.
            coord_y = cube.coord(axis='Y', dim_coords=True)
            data = cube.data
            if np.diff(coord_y.bounds[0]) > 0:
                data = cube.data[::-1, :]
            im = PIL.Image.open(temp_filename)
            im_data = np.array(im)
            # Currently we only support writing 32-bit tiff, when comparing
            # the data ensure that it is also 32-bit
            np.testing.assert_array_equal(im_data,
                                          data.astype(np.float32))

    def test_unmasked(self):
        tif_header = 'SMALL_total_column_co2.nc.tif_header.txt'
        fin = tests.get_data_path(('NetCDF', 'global', 'xyt',
                                   'SMALL_total_column_co2.nc'))
        cube = iris.load_cube(fin)[0]
        # PIL doesn't support float64
        cube.data = cube.data.astype('f4')

        # Ensure longitude values are continuous and monotonically increasing,
        # and discard the 'half cells' at the top and bottom of the UM output
        # by extracting a subset.
        east = iris.Constraint(longitude=lambda cell: cell < 180)
        non_edge = iris.Constraint(latitude=lambda cell: -90 < cell < 90)
        cube = cube.extract(east & non_edge)
        cube.coord('longitude').guess_bounds()
        cube.coord('latitude').guess_bounds()
        self.check_tiff(cube, tif_header)

        # Check again with the latitude coordinate (and the corresponding
        # cube.data) inverted. The output should be the same as before.
        coord = cube.coord('latitude')
        coord.points = coord.points[::-1]
        coord.bounds = None
        coord.guess_bounds()
        cube.data = cube.data[::-1, :]
        self.check_tiff(cube, tif_header)

    def test_masked(self):
        tif_header = 'SMALL_total_column_co2.nc.ma.tif_header.txt'
        fin = tests.get_data_path(('NetCDF', 'global', 'xyt',
                                   'SMALL_total_column_co2.nc'))
        cube = iris.load_cube(fin)[0]
        # PIL doesn't support float64
        cube.data = cube.data.astype('f4')

        # Repeat the same data extract as above
        east = iris.Constraint(longitude=lambda cell: cell < 180)
        non_edge = iris.Constraint(latitude=lambda cell: -90 < cell < 90)
        cube = cube.extract(east & non_edge)
        cube.coord('longitude').guess_bounds()
        cube.coord('latitude').guess_bounds()
        # Mask some of the data
        cube.data = np.ma.masked_where(cube.data <= 380, cube.data)
        self.check_tiff(cube, tif_header)


class Test_export_shapefile(tests.IrisTest):
    def test_basic_unrotated(self):
        # Get a small sample cube on a simple latlon projection
        cube = istk.simple_pp()
        # Take just a small section of the cube
        cube = cube[::10, ::10]
        cube = cube[1:5, 1:4]

#        test_filepath = '/net/home/h05/itpp/Iris/sprints/20131028_new-agile_and_shapefiles/scit322_shapefiles_geotiff/tmp_out/test'
#        export_shapefile(cube, test_filepath)

        mock_shapefile_module = mock.Mock(spec=['Writer', 'POINT'])
        mock_shapefile_writer = mock.Mock(
            spec=['field', 'record', 'point', 'save'])
        mock_shapefile_module.Writer = mock.Mock(
            return_value=mock_shapefile_writer)
        test_filepath = 'an/arbitrary/file_path'
        with mock.patch('iris.experimental.shapefiles.shapefile',
                        mock_shapefile_module):
            export_shapefile(cube, test_filepath)

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
        # pull out x values from all calls to writer.point
        x_vals = [mock_call[1][0]
                  for mock_call in mock_shapefile_writer.mock_calls
                  if mock_call[0] == 'point']
        # pull out y values from all calls to writer.point
        y_vals = [mock_call[1][1]
                  for mock_call in mock_shapefile_writer.mock_calls
                  if mock_call[0] == 'point']
        # pull out data values from all calls to writer.record
        data_vals = [mock_call[1][0]
                     for mock_call in mock_shapefile_writer.mock_calls
                     if mock_call[0] == 'record']
        # Check values as expected
        self.assertArrayAllClose(np.array(x_vals)[[0, 4, 8]],
                                 cube.coord('longitude').points)
        self.assertArrayAllClose(np.array(y_vals)[[0, 3, 6, 9]],
                                 cube.coord('latitude').points)
        self.assertArrayAllClose(data_vals, cube.data.flat)

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

if __name__ == "__main__":
    tests.main()
