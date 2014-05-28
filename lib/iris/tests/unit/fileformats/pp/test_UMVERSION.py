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
"""Unit tests for :class:`iris.fileformats.pp.UMVERSION`."""

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests

from iris.fileformats.pp import UMVERSION


class Test___init__(tests.IrisTest):
    def _check_init(self, umver, *content):
        major, minor, unknown = content
        self.assertEqual(umver.major, major)
        self.assertEqual(umver.minor, minor)
        self.assertEqual(umver.unknown, unknown)

    def test_simple(self):
        umver = UMVERSION(2, 5)
        self._check_init(umver, 2, 5, False)

    def test_unknown(self):
        umver = UMVERSION(2, 5, unknown=True)
        self._check_init(umver, 0, 0, True)

    def test_float(self):
        umver = UMVERSION(2.0000001, 4.9999999)
        self._check_init(umver, 2, 5, False)

    def test_fail_float(self):
        with self.assertRaises(ValueError) as err_context:
            umver = UMVERSION(2.3, 4)
        msg = err_context.exception.message
        self.assertIn('both', msg)
        self.assertIn('integers', msg)

    def test_fail_negative(self):
        with self.assertRaises(ValueError) as err_context:
            umver = UMVERSION(2, -4)
        msg = err_context.exception.message
        self.assertIn('both', msg)
        self.assertIn('positive', msg)

    def test_fail_minor_range(self):
        with self.assertRaises(ValueError) as err_context:
            umver = UMVERSION(2, 105)
        msg = err_context.exception.message
        self.assertIn('minor', msg)
        self.assertIn('99', msg)


class Test___str__(tests.IrisTest):
    def test_simple(self):
        self.assertEqual(str(UMVERSION(2, 5)), '2.5')

    def test_unknown(self):
        self.assertEqual(str(UMVERSION(2, 5, unknown=True)), '')


class Test_lbsrce(tests.IrisTest):
    def test_simple(self):
        self.assertEqual(UMVERSION(2, 5).lbsrce(), 2051111)

    def test_unknown(self):
        self.assertEqual(UMVERSION(2, 5, unknown=True).lbsrce(), 0)


class Test_from_lbsrce(tests.IrisTest):
    def _check_lbsrce(self, umver, content, string, lbsrce):
        major, minor, unknown = content
        self.assertEqual(umver.major, major)
        self.assertEqual(umver.minor, minor)
        self.assertEqual(umver.unknown, unknown)
        self.assertEqual(str(umver), string)
        self.assertEqual(umver.lbsrce(), lbsrce)

    def test_simple(self):
        umver = UMVERSION.from_lbsrce(2051111)
        self._check_lbsrce(umver,
                           (2, 5, False),
                           '2.5',
                           2051111)

    def test_no_version(self):
        umver = UMVERSION.from_lbsrce(1111)
        self._check_lbsrce(umver,
                           (0, 0, False),
                           '0.0',
                           1111)

    def test_unknown(self):
        umver = UMVERSION.from_lbsrce(123)
        self._check_lbsrce(umver,
                           (0, 0, True),
                           '',
                           0)


if __name__ == "__main__":
    tests.main()
