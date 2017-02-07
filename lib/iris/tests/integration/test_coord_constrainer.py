# (C) British Crown Copyright 2017, Met Office
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
"""
Integration tests for :class:`iris._constraints.CoordConstraintHelper`

Also exercising the new :meth:`cube.cut`.

"""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests

import numpy as np

import iris
from iris.cube import Cube
from iris.coords import DimCoord
from iris.tests import get_data_path
from iris import Constraint, COORD_CONSTRAINER as CC


class Test(tests.IrisTest):
    def show(self, cube, comment,
             show_cube=False, show_coords=True, int_coords=True,
             show_lats=True, show_lons=True):
        print()
        print(comment)
        if show_cube:
            print('cube = \n', cube)
        if show_coords:
            lons = cube.coord('longitude').points
            lats = cube.coord('latitude').points
            if int_coords:
                lons = lons.astype(int)
                lats = lats.astype(int)
            if show_lons:
                print('lons = ', lons)
            if show_lats:
                print('lats = ', lats)

    def test(self):
        # A few tests to exercise the new stuff -- not proper tests, yet.
        path = get_data_path(('PP', 'simple_pp', 'global.pp'))
        cube = iris.load_cube(path)

        cube = cube[::4, ::4]
        self.show(cube, 'original:', show_cube=True, int_coords=False)

        msg = """\
test cube.extract :
   = cube.extract(Constraint(longitude=lambda cell: cell > 120.0,
                             latitude=lambda cell: -10 <= cell < 40))
"""
        subcube = cube.extract(
            Constraint(longitude=lambda cell: cell > 120.0,
                       latitude=lambda cell: -10 <= cell < 40))
        self.show(subcube, msg)

        #
        # Test the equivalent using the new facilities.
        #
        msg = """\
print 'CC version'
  = cube.cut(longitude=CC > 120.0, latitude=CC[-10:40])
"""
        subcube_cc = cube.cut(longitude=CC > 120.0, latitude=CC[-10:40])
        self.show(subcube_cc, msg)
        same = subcube_cc == subcube
        print('?same? : ', same)
        self.assertTrue(same)

        subcube = cube.extract(Constraint(longitude=CC.near(130)))
        self.show(subcube, 'lons=CC.near(130)', show_lats=False)

        msg = 'cut(lon=CC > 300, lat=CC.between(-10,40)) :'
        subcube = cube.cut(longitude=CC > 300, latitude=CC.between(-10, 40))
        self.show(subcube, msg)
        self.assertArrayAllClose(subcube.coord('longitude').points,
                                 [315, 330, 345], atol=0.01)
        self.assertArrayAllClose(subcube.coord('latitude').points,
                                 [30, 20, 10,  0, -10], atol=0.01)

        # Test the indexing form of the range operator.
        msg = 'cut(lat=CC[-10:40]) :'
        subcube = cube.cut(longitude=CC > 300, latitude=CC[-10:40])
        self.show(subcube, msg, show_lons=False)
        self.assertArrayAllClose(subcube.coord('latitude').points,
                                 [30, 20, 10,  0, -10], atol=0.01)

        msg = 'cut(lat=CC[-10:40]) :'
        subcube = cube.cut(latitude=CC[-10:40])
        self.show(subcube, msg, show_lons=False)
        self.assertArrayAllClose(subcube.coord('latitude').points,
                                 [30, 20, 10,  0, -10], atol=0.01)

        subcube = cube.cut(longitude=164.99995422)
        msg = 'cut(lon=164.99995422):'
        self.show(subcube, msg, show_cube=True, show_coords=False)
        self.assertIsNone(subcube)

        msg = 'cut(lon=CC(165)):'
        subcube = cube.cut(longitude=CC(165))
        self.show(subcube, msg, show_lats=False)
        self.assertArrayAllClose(subcube.coord('longitude').points,
                                 [164.999954])

        msg = 'cut(lon=CC ^ 165, lat=CC ^ 100):'
        subcube = cube.cut(longitude=CC ^ 165, latitude=CC ^ 100)
        self.show(subcube, msg)
        self.assertArrayAllClose(subcube.coord('longitude').points,
                                 [165], atol=0.01)
        self.assertArrayAllClose(subcube.coord('latitude').points,
                                 [90], atol=0.01)

        msg = 'cut(lon=CC >= 165):'
        subcube = cube.cut(longitude=CC >= 165)
        self.show(subcube, msg, show_lats=False)
        self.assertArrayAllClose(subcube.coord('longitude').points,
                                 np.arange(180, 360, 15), atol=0.01)

        msg = 'cut(lon=CC < 165):'
        subcube = cube.cut(longitude=CC < 165)
        self.show(subcube, msg, show_lats=False)
        self.assertArrayAllClose(subcube.coord('longitude').points,
                                 np.arange(0, 165.1, 15), atol=0.01)
        # N.B. last point is at ~165, because it is a bit under the value.
        self.assertArrayAllClose(subcube.coord('longitude').points[-1],
                                 [164.999954])

    def test_index_range(self):
        # Test precise forms of range specifier for indexing.
        cube = Cube(np.arange(10))
        cube.add_dim_coord(DimCoord(np.arange(10, dtype=int), 'longitude'), 0)
        cube.add_aux_coord(DimCoord([0], 'latitude'))

        msg = '0..9, cut(lons=[3:7]) :'
        subcube = cube.cut(longitude=CC[3:7])
        self.show(subcube, msg, show_lats=False)
        self.assertArrayEqual(subcube.coord('longitude').points,
                              [3, 4, 5, 6])

        msg = '0..9, cut(lons=[3:7], "[)") :'
        subcube = cube.cut(longitude=CC[3:7, "[)"])
        self.show(subcube, msg, show_lats=False)
        self.assertArrayEqual(subcube.coord('longitude').points,
                              [3, 4, 5, 6])

        msg = '0..9, cut(lons=[3:7, "()"]) :'
        subcube = cube.cut(longitude=CC[3:7, "()"])
        self.show(subcube, msg, show_lats=False)
        self.assertArrayEqual(subcube.coord('longitude').points,
                              [4, 5, 6])

        msg = '0..9, cut(lons=[3:7, "[]"]) :'
        subcube = cube.cut(longitude=CC[3:7, "[]"])
        self.show(subcube, msg, show_lats=False)
        self.assertArrayEqual(subcube.coord('longitude').points,
                              [3, 4, 5, 6, 7])

        msg = '0..9, cut(lons=[3:7, "(]"]) :'
        subcube = cube.cut(longitude=CC[3:7, "(]"])
        self.show(subcube, msg, show_lats=False)
        self.assertArrayEqual(subcube.coord('longitude').points,
                              [4, 5, 6, 7])


if __name__ == '__main__':
    tests.main()
