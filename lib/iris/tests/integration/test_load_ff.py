from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

import iris.tests as tests
import iris

class TestFF(tests.IrisTest):
    @tests.skip_data
    def test_basic_ff_load(self):
        file_path = tests.get_data_path(('FF', 'n48_multi_field'))
        cubes = iris.load(file_path)

        self.assertEqual(len(cubes), 4)

        shape = (73, 96)
        cube = cubes[0]
        self.assertEqual(cube.name(), 'air_temperature')
        self.assertEqual(cube.shape, shape)
        self.assertArrayShapeStats(cube, shape, 280.9620, 20.23819)

        cube = cubes[1]
        self.assertEqual(cube.name(), 'air_temperature')
        self.assertEqual(cube.shape, shape)
        self.assertArrayShapeStats(cube, shape, 281.84446, 20.13238)

#        cube = cubes[2]
#        self.assertEqual(cube.name(), 'soil_temperature')
#        self.assertEqual(cube.shape, shape)
#        # This one has a problem ?
#        self.assertArrayShapeStats(cube, shape, -708933044., 508551961.)

        cube = cubes[3]
        self.assertEqual(cube.name(), 'surface_altitude')
        self.assertEqual(cube.shape, shape)
        self.assertArrayShapeStats(cube, shape, 377.9390, 827.8499)



    @tests.skip_data
    def test_soilcube_fails(self):
        file_path = tests.get_data_path(('FF', 'n48_multi_field'))
        cubes = iris.load(file_path)
        cube = cubes[2]
        shape = (73, 96)
        self.assertEqual(cube.name(), 'soil_temperature')
        self.assertEqual(cube.shape, shape)
        # This one has a problem ?
        self.assertArrayShapeStats(cube, shape, 269.7401, 31.0357)


if __name__ == '__main__':
    tests.main()
