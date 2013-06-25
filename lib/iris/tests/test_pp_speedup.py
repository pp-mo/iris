# (C) British Crown Copyright 2010 - 2013, Met Office
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


# import iris tests first so that some things can be initialised before importing anything else
#import iris.tests as tests

import numpy as np

import iris

from pp_utils import TimedBlock

TEST_SPEED_DATADIR = '/net/home/h05/itpp/Iris/sprints/sprint_11_ppspeed_20130619/scit222_pp_convert_speed/linked_data'
TEST_FULLDATA_FILEPATH = TEST_SPEED_DATADIR + '/eacvs.uv5.pp'
TEST_PARTDATA_FILEPATH = TEST_SPEED_DATADIR + '/test.pp'
TEST_LARGER_PARTDATA_FILEPATH = TEST_SPEED_DATADIR + '/test_larger.pp'
TEST_ONEFIELD_FILEPATH = TEST_SPEED_DATADIR + '/onecube.pp'

def testit():
#    test_filepath = TEST_LARGER_PARTDATA_FILEPATH
#    test_filepath = TEST_PARTDATA_FILEPATH
    test_filepath = TEST_ONEFIELD_FILEPATH

    print 'Pre-loading...'
    cube = iris.load_cube(test_filepath, 'eastward_wind')
    print cube

    test_filepath = TEST_PARTDATA_FILEPATH
#    print
#    print 'Raw load with timing (caching enabled)...'
#    iris.fileformats.rules.ENABLE_RULE_RESULT_CACHING = True
#    with TimedBlock() as block_timer:
#        cube = iris.load_raw(test_filepath, 'eastward_wind')
#    t_with = block_timer.seconds()
#    print '  load time:', t_with
#    print

    n_retries = 5
    t_with_all = []
    t_without_all = []
    for i_retry in range(n_retries):
        print
        print 'Raw load with timing (enabled)...'
        iris.fileformats.rules.ENABLE_RULE_RESULT_CACHING = True
        with TimedBlock() as block_timer:
            cube = iris.load_raw(test_filepath, 'eastward_wind')
        t_with = block_timer.seconds()
        print '  load time:', t_with
        print
        print 'Re-load with timing (DISABLED)...'
        iris.fileformats.rules.ENABLE_RULE_RESULT_CACHING = False
        with TimedBlock() as block_timer:
            cube = iris.load_raw(test_filepath, 'eastward_wind')
        t_without = block_timer.seconds()
        print '  load time:', t_without
        t_with_all += [t_with]
        t_without_all += [t_without]
    print
    t_with_avg = np.mean(t_with_all)
    t_without_avg = np.mean(t_without_all)
    t_with_sd = np.std(t_with_all)
    t_without_sd = np.std(t_without_all)
    print 'with = ', t_with_all
    print 'without = ', t_without_all
    fmt = 'Over {}, avg with :: without = {:.3f} :: {:.3f} (+/-{:.3f}::{:.3f})'
    print fmt.format(n_retries,
                     t_with_avg, t_without_avg,
                     t_with_sd, t_without_sd)
    print 'Rough saving = {:5.1f}%'.format(
        100.0 * (t_without_avg - t_with_avg) / t_without_avg)

if __name__ == "__main__":
    testit()
