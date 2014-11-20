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
"""Integration tests for loading UM FieldsFile variants."""

from __future__ import (absolute_import, division, print_function)

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests

import shutil

import numpy as np

from iris.experimental.um import (Field, Field2, Field3, FieldsFileVariant,
                                  FixedLengthHeader)


IMDI = -32768
RMDI = -1073741824.0


@tests.skip_data
class TestRead(tests.IrisTest):
    def load(self):
        path = tests.get_data_path(('FF', 'n48_multi_field'))
        return FieldsFileVariant(path)

    def test_fixed_length_header(self):
        ffv = self.load()
        self.assertEqual(ffv.fixed_length_header.dataset_type, 3)
        self.assertEqual(ffv.fixed_length_header.lookup_shape, (64, 5))

    def test_integer_constants(self):
        ffv = self.load()
        expected = [IMDI, IMDI, IMDI, IMDI, IMDI,  # 1 - 5
                    96, 73, 70, 70, 4,             # 6 - 10
                    IMDI, 70, 50, IMDI, IMDI,      # 11 - 15
                    IMDI, 2, IMDI, IMDI, IMDI,     # 16 - 20
                    IMDI, IMDI, IMDI, 50, 2381,    # 21 - 25
                    IMDI, IMDI, 4, IMDI, IMDI,     # 26 - 30
                    IMDI, IMDI, IMDI, IMDI, IMDI,  # 31 - 35
                    IMDI, IMDI, IMDI, IMDI, IMDI,  # 36 - 40
                    IMDI, IMDI, IMDI, IMDI, IMDI,  # 41 - 45
                    IMDI]                          # 46
        self.assertArrayEqual(ffv.integer_constants, expected)

    def test_real_constants(self):
        ffv = self.load()
        expected = [3.75, 2.5, -90.0, 0.0, 90.0,      # 1 - 5
                    0.0, RMDI, RMDI, RMDI, RMDI,      # 6 - 10
                    RMDI, RMDI, RMDI, RMDI, RMDI,     # 11 - 15
                    80000.0, RMDI, RMDI, RMDI, RMDI,  # 16 - 20
                    RMDI, RMDI, RMDI, RMDI, RMDI,     # 21 - 25
                    RMDI, RMDI, RMDI, RMDI, RMDI,     # 26 - 30
                    RMDI, RMDI, RMDI, RMDI, RMDI,     # 31 - 35
                    RMDI, RMDI, RMDI]                 # 36 - 38
        self.assertArrayEqual(ffv.real_constants, expected)

    def test_level_dependent_constants(self):
        ffv = self.load()
        # To make sure we have the correct Fortran-order interpretation
        # we just check the overall shape and a few of the values.
        self.assertEqual(ffv.level_dependent_constants.shape, (71, 8))
        expected = [0.92, 0.918, 0.916, 0.912, 0.908]
        self.assertArrayEqual(ffv.level_dependent_constants[:5, 2], expected)

    def test_fields__length(self):
        ffv = self.load()
        self.assertEqual(len(ffv.fields), 5)

    def test_fields__superclass(self):
        ffv = self.load()
        fields = ffv.fields
        for field in fields:
            self.assertIsInstance(field, Field)

    def test_fields__specific_classes(self):
        ffv = self.load()
        fields = ffv.fields
        for i in range(4):
            self.assertIs(type(fields[i]), Field3)
        self.assertIs(type(fields[4]), Field)

    def test_fields__header(self):
        ffv = self.load()
        self.assertEqual(ffv.fields[0].lbfc, 16)

    def test_fields__data_wgdos(self):
        ffv = self.load()
        data = ffv.fields[0].read_data()
        self.assertEqual(data.shape, (73, 96))
        self.assertArrayEqual(data[2, :3], [223.5, 223.0, 222.5])

    def test_fields__data_not_packed(self):
        path = tests.get_data_path(('FF', 'ancillary', 'qrparm.mask'))
        ffv = FieldsFileVariant(path)
        data = ffv.fields[0].read_data()
        expected = [[1, 1, 1],
                    [1, 1, 1],
                    [0, 1, 1],
                    [0, 1, 1],
                    [0, 1, 1],
                    [0, 1, 1],
                    [0, 1, 1],
                    [0, 1, 1],
                    [0, 1, 1],
                    [0, 1, 1],
                    [0, 0, 1]]
        self.assertArrayEqual(data[:11, 605:608], expected)


@tests.skip_data
class TestUpdate(tests.IrisTest):
    def test_fixed_length_header(self):
        # Check that tweaks to the fixed length header are reflected in
        # the output file.
        src_path = tests.get_data_path(('FF', 'n48_multi_field'))
        with self.temp_filename() as temp_path:
            shutil.copyfile(src_path, temp_path)
            ffv = FieldsFileVariant(temp_path, FieldsFileVariant.UPDATE_MODE)
            self.assertEqual(ffv.fixed_length_header.sub_model, 1)
            ffv.fixed_length_header.sub_model = 2
            ffv.close()

            ffv = FieldsFileVariant(temp_path)
            self.assertEqual(ffv.fixed_length_header.sub_model, 2)

    def test_fixed_length_header_wrong_dtype(self):
        # Check that using the wrong dtype in the fixed length header
        # doesn't confuse things.
        src_path = tests.get_data_path(('FF', 'n48_multi_field'))
        with self.temp_filename() as temp_path:
            shutil.copyfile(src_path, temp_path)
            ffv = FieldsFileVariant(temp_path, FieldsFileVariant.UPDATE_MODE)
            header_values = ffv.fixed_length_header.raw
            self.assertEqual(header_values.dtype, '>i8')
            header = FixedLengthHeader(header_values.astype('<i4'))
            ffv.fixed_length_header = header
            ffv.close()

            ffv = FieldsFileVariant(temp_path)
            # If the header was written out with the wrong dtype this
            # value will go crazy - so check that it's still OK.
            self.assertEqual(ffv.fixed_length_header.sub_model, 1)

    def test_integer_constants(self):
        # Check that tweaks to the integer constants are reflected in
        # the output file.
        src_path = tests.get_data_path(('FF', 'n48_multi_field'))
        with self.temp_filename() as temp_path:
            shutil.copyfile(src_path, temp_path)
            ffv = FieldsFileVariant(temp_path, FieldsFileVariant.UPDATE_MODE)
            self.assertEqual(ffv.integer_constants[5], 96)
            ffv.integer_constants[5] = 95
            ffv.close()

            ffv = FieldsFileVariant(temp_path)
            self.assertEqual(ffv.integer_constants[5], 95)

    def test_integer_constants_wrong_dtype(self):
        # Check that using the wrong dtype in the integer constants
        # doesn't cause mayhem!
        src_path = tests.get_data_path(('FF', 'n48_multi_field'))
        with self.temp_filename() as temp_path:
            shutil.copyfile(src_path, temp_path)
            ffv = FieldsFileVariant(temp_path, FieldsFileVariant.UPDATE_MODE)
            self.assertEqual(ffv.integer_constants.dtype, '>i8')
            ffv.integer_constants = ffv.integer_constants.astype('<f4')
            ffv.close()

            ffv = FieldsFileVariant(temp_path)
            # If the integer constants were written out with the wrong
            # dtype this value will go crazy - so check that it's still
            # OK.
            self.assertEqual(ffv.integer_constants[5], 96)

    def test_real_constants(self):
        # Check that tweaks to the real constants are reflected in the
        # output file.
        src_path = tests.get_data_path(('FF', 'n48_multi_field'))
        with self.temp_filename() as temp_path:
            shutil.copyfile(src_path, temp_path)
            ffv = FieldsFileVariant(temp_path, FieldsFileVariant.UPDATE_MODE)
            self.assertEqual(ffv.real_constants[1], 2.5)
            ffv.real_constants[1] = 14.75
            ffv.close()

            ffv = FieldsFileVariant(temp_path)
            self.assertEqual(ffv.real_constants[1], 14.75)

    def test_real_constants_wrong_dtype(self):
        # Check that using the wrong dtype in the real constants doesn't
        # cause mayhem!
        src_path = tests.get_data_path(('FF', 'n48_multi_field'))
        with self.temp_filename() as temp_path:
            shutil.copyfile(src_path, temp_path)
            ffv = FieldsFileVariant(temp_path, FieldsFileVariant.UPDATE_MODE)
            self.assertEqual(ffv.real_constants.dtype, '>f8')
            ffv.real_constants = ffv.real_constants.astype('<i4')
            ffv.close()

            ffv = FieldsFileVariant(temp_path)
            # If the real constants were written out with the wrong
            # dtype this value will go crazy - so check that it's still
            # OK.
            self.assertEqual(ffv.real_constants[1], 2)

    def test_level_dependent_constants(self):
        # Check that tweaks to the level dependent constants are
        # reflected in the output file.
        # NB. Because it is a multi-dimensional component, this is
        # sensitive to the Fortran vs C array ordering used to write
        # the file.
        src_path = tests.get_data_path(('FF', 'n48_multi_field'))
        with self.temp_filename() as temp_path:
            shutil.copyfile(src_path, temp_path)
            ffv = FieldsFileVariant(temp_path, FieldsFileVariant.UPDATE_MODE)
            self.assertEqual(ffv.level_dependent_constants[3, 2], 0.912)
            ffv.level_dependent_constants[3, 2] = 0.913
            ffv.close()

            ffv = FieldsFileVariant(temp_path)
            self.assertEqual(ffv.level_dependent_constants[3, 2], 0.913)


class TestCreate(tests.IrisTest):
    @tests.skip_data
    def test_copy(self):
        # Checks that copying all the attributes to a new file
        # re-creates the original with minimal differences.
        src_path = tests.get_data_path(('FF', 'ancillary', 'qrparm.mask'))
        ffv_src = FieldsFileVariant(src_path, FieldsFileVariant.READ_MODE)
        with self.temp_filename() as temp_path:
            ffv_dest = FieldsFileVariant(temp_path,
                                         FieldsFileVariant.CREATE_MODE)
            ffv_dest.fixed_length_header = ffv_src.fixed_length_header
            for name, kind in FieldsFileVariant._COMPONENTS:
                setattr(ffv_dest, name, getattr(ffv_src, name))
            ffv_dest.fields = ffv_src.fields
            ffv_dest.close()

            # Compare the files at a binary level.
            src = np.fromfile(src_path, dtype='>i8', count=-1)
            dest = np.fromfile(temp_path, dtype='>i8', count=-1)
            changed_indices = np.where(src != dest)[0]
            # Allow for acceptable differences.
            self.assertArrayEqual(changed_indices, [110, 111, 125, 126, 130,
                                                    135, 140, 142, 144, 160])
            # All but the last difference is from the use of IMDI
            # instead of 1 to mark an unused dimension length.
            self.assertArrayEqual(dest[changed_indices[:-1]], [IMDI] * 9)
            # The last difference is to the length of the DATA component
            # because we've padded the last field.
            self.assertEqual(dest[160], 956416)

    def test_create(self):
        # Check we can create a new file from scratch, with the correct
        # cross-referencing automatically applied to the headers to
        # enable it to load again.
        with self.temp_filename() as temp_path:
            temp_path = 'test.ff'
            ffv = FieldsFileVariant(temp_path, FieldsFileVariant.CREATE_MODE)
            ffv.fixed_length_header = FixedLengthHeader([-1] * 256)
            ffv.fixed_length_header.data_set_format_version = 20
            ffv.fixed_length_header.sub_model = 1
            ffv.fixed_length_header.dataset_type = 3
            constants = IMDI * np.ones(46, dtype=int)
            constants[5] = 4
            constants[6] = 5
            ffv.integer_constants = constants
            ints = IMDI * np.ones(45, dtype=int)
            ints[17] = 4  # LBROW
            ints[18] = 5  # LBNPT
            ints[20] = 0  # LBPACK
            ints[21] = 2  # LBREL
            ints[38] = 1  # LBUSER(1)
            reals = range(19)
            src_data = np.arange(20, dtype='f4').reshape((4, 5))
            ffv.fields = [Field2(ints, reals, src_data)]
            ffv.close()

            ffv = FieldsFileVariant(temp_path)
            # Fill with -1 instead of IMDI so we can detect where IMDI
            # values are being automatically set.
            expected = -np.ones(256, dtype=int)
            expected[0] = 20
            expected[1] = 1
            expected[4] = 3
            expected[99:101] = (257, 46)  # Integer constants
            expected[104:106] = IMDI
            expected[109:112] = IMDI
            expected[114:117] = IMDI
            expected[119:122] = IMDI
            expected[124:127] = IMDI
            expected[129:131] = IMDI
            expected[134:136] = IMDI
            expected[139:145] = IMDI
            expected[149:152] = (303, 64, 1)  # 303 = 256 + 46 + 1
            expected[159:161] = (2049, 2048)
            # Compare using lists because we get more helpful error messages!
            self.assertEqual(list(ffv.fixed_length_header.raw), list(expected))
            self.assertArrayEqual(ffv.integer_constants, constants)
            self.assertIsNone(ffv.real_constants)
            self.assertEqual(len(ffv.fields), 1)
            for field in ffv.fields:
                data = field.read_data()
                self.assertArrayEqual(data, src_data)


if __name__ == '__main__':
    tests.main()
