# (C) British Crown Copyright 2014, Met Office
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
"""Unit tests for the `iris.fileformats.pp_packing.pack_field` function."""

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests

import numpy as np
from iris.fileformats.pp_packing import pack_field, wgdos_unpack, \
    PACKING_TYPE_NONE, PACKING_TYPE_WGDOS, BYTES_PER_PP_WORD


# NOTE: form of the call (no keywords)
#   = pack_field(pack_method, data, lbrow, lbnpt, bmdi, bpacc, n_bits)

class TestPackField(tests.IrisTest):
    def setUp(self):
        # Create test data matching C single floats (bytes must be right).
        test_vals = np.array([[77.3, 2.1, 3.0, 4.0],
                              [999.0005, 999.0006, 999.0007, 999.0008],
                              [99999.03, 999.04, 9.05, 0.06]],
                             dtype=np.float32)

        # NOTE: As it is, this is too small to work.
        # NOTE: this is a problem with the library interface -- it makes no
        # test to ensure that the packed result is smaller than the original,
        # and if it is not you can just blow up....
        #
        # So, we add some extra zeroes into the test array to make it work...

        # Replicate the array to expand along the 'x' axis.
        nx = test_vals.shape[-1]
        test_array = np.repeat(test_vals, 5, axis=-1)
        # Fill all but the first repeat with zeroes.
        test_array[..., nx:] = 0

        # Save results for testing
        self.test_array = test_array
        self.ny = self.test_array.shape[0]
        self.nx = self.test_array.shape[1]
        self.mdi = 1.07e30

    def test_nopack(self):
        # NOTE: form of the call (no keywords)
        #   = pack_field(pack_method, data, lbrow, lbnpt, bmdi, bpacc, n_bits)
        result = pack_field(PACKING_TYPE_NONE,
                            self.test_array, self.ny, self.nx,  # array details
                            self.mdi,  # mdi value
                            2,  # packing accuracy = n-bits
                            0)  # n_bits (unused)
        self.assertEqual(result.dtype, np.byte)
        # Compare result bytes to the original (in the PP big-endian form).
        bytes_in = self.test_array.astype('>f4').tostring()
        bytes_out = result.tostring()
        self.assertArrayEqual(bytes_out, bytes_in)

    def test_wgdos_pack_unpack(self):
        # Set "typical" accuracy value for test, and matching tolerance level.
        accuracy_bits = 6
            #
            # NOTE:
            # If you increase this to 8 bits, it coredumps.  7 "seems ok".
            # THIS IS NOT NICE.
            #
        # NOTE: form of the call (no keywords)
        #   = pack_field(pack_method, data, lbrow, lbnpt, bmdi, bpacc, n_bits)
        result = pack_field(PACKING_TYPE_WGDOS,
                            self.test_array, self.ny, self.nx,  # array details
                            1.07e30,  # mdi value
                            -accuracy_bits,  # packing accuracy = n-bits
                            0)  # n_bits (unused)
        original_size = len(self.test_array.tostring())
        result_size = len(result.tostring())
#        print '\nSizes: original={}, result={}'.format(
#            original_size, result_size)
        self.assertLess(result_size, original_size)
        # Check we can reverse the operation
        # NOTE: form of the call (no keywords)
        #   = wgdos_unpack(byte_array, lbrow, lbnpt, mdi)
        unwind = wgdos_unpack(result, self.ny, self.nx, self.mdi)
        # Calculate appropriate tolerance for test
        rel_tol = 1.0 / 2**accuracy_bits
#        print '\n\noriginal data:\n', self.test_array
#        print '\npacked+unpacked data:\n', unwind
        self.assertArrayAllClose(self.test_array, unwind, rtol=rel_tol)


if __name__ == "__main__":
    tests.main()
