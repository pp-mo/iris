from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

import iris.tests as tests
import iris

from iris.fileformats.um._ff_replacement import FF2PP as using_ff2pp
from iris.fileformats._ff import FF2PP as old_iris_ff2pp


class TestFF(tests.IrisTest):
    @tests.skip_data
    def test_basic_ff_load(self):
        file_path = tests.get_data_path(('FF', 'n48_multi_field'))
        cubes = iris.load(file_path)

        self.assertEqual(len(cubes), 4)

        old_match = "==" if (using_ff2pp == old_iris_ff2pp) else "!="
        print('\n\nUsed ff function {} old ff.FF2PP\n\n'.format(old_match))

        shape = (73, 96)
        cube = cubes[0]
        self.assertEqual(cube.name(), 'air_temperature')
        self.assertEqual(cube.shape, shape)
        self.assertArrayShapeStats(cube, shape, 280.9620, 20.23819)

        cube = cubes[1]
        self.assertEqual(cube.name(), 'air_temperature')
        self.assertEqual(cube.shape, shape)
        self.assertArrayShapeStats(cube, shape, 281.84446, 20.13238)

        cube = cubes[2]
        self.assertEqual(cube.name(), 'soil_temperature')
        self.assertEqual(cube.shape, shape)
        # This one has a problem ?
        self.assertArrayShapeStats(cube, shape, 269.7401, 31.0357)

        cube = cubes[3]
        self.assertEqual(cube.name(), 'surface_altitude')
        self.assertEqual(cube.shape, shape)
        self.assertArrayShapeStats(cube, shape, 377.9390, 827.8499)


if __name__ == '__main__':
    tests.main()
