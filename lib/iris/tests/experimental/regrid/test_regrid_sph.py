# (C) British Crown Copyright 2013 Met Office
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
Conservative regrid tests for 'spherical_geometry' operation.
"""

# import iris tests first so that some things can be initialised
# before importing anything else.
import iris.tests as tests

import iris.experimental.regrid_conservative_sphtrig

import iris.tests.experimental.regrid.generic_conservative_regrid_tests as regrid_tests

class TestConservativeRegridSph(regrid_tests.GenericConservativeRegridTester, 
                                tests.IrisTest):    
    # Override init to set up the 'switched' parts of the operation.
    def __init__(self, *args, **kwargs):
        # Define an id to guide testee-specific test behaviour
        self.testee_id = 'sph_trig'
        # Define the testee regrid call which all the tests call
        self.regrid_call = \
            iris.experimental.regrid_conservative_sphtrig.regrid_conservative_via_sph
        super(self, TestConservativeRegridEsmf).__init__(*args, **kwargs)


if __name__ == '__main__':
    tests.main()
