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
Conservative regrid tests for ESMPy operation.
"""

# import iris tests first so that some things can be initialised
# before importing anything else.
import iris.tests as tests

# Import ESMF if installed, else fail quietly + disable all the tests.
try:
    import ESMF
    import iris.experimental.regrid_conservative
    skip_esmf = lambda f: f
except ImportError:
    ESMF = None
    skip_esmf = unittest.skip(
        reason='Requires ESMF module, which is not available.')

@skip_esmf
class TestConservativeRegridEsmf(test_esmf.TestConservativeRegrid, 
                                 tests.IrisTest):    
    # Override init to set up the 'switched' parts of the operation.
    def __init__(self, *args, **kwargs):
        # Define an id to guide testee-specific test behaviour
        self.testee_id = 'esmpy'
        # Define the testee regrid call which all the tests call
        self.regrid_call = \
            iris.experimental.regrid_conservative.regrid_conservative_via_esmpy
        super(self, TestConservativeRegridEsmf).__init__(*args, **kwargs)

    # Define esmpy-specific one-time setup + teardown operations.
    @classmethod
    def setUpClass(cls):
        # Pre-initialise ESMF, just to avoid warnings about no logfile.
        # NOTE: noisy if logging is off, and no control of filepath.  Boo!!
        self._emsf_logfile_path = os.path.join(os.getcwd(), 'ESMF_LogFile')
        ESMF.Manager(logkind=ESMF.LogKind.SINGLE, debug=False)

    @classmethod
    def tearDownClass(cls):
        # remove the logfile if we can, just to be tidy
        if os.path.exists(self._emsf_logfile_path):
            os.remove(self._emsf_logfile_path)


if __name__ == '__main__':
    tests.main()
