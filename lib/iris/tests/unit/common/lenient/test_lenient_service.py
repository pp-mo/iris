# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""
Unit tests for the :func:`iris.common.lenient.lenient_service`.

"""

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests

from inspect import getmodule
from unittest.mock import sentinel

from iris.common.lenient import LENIENT, lenient_service


class Test(tests.IrisTest):
    def setUp(self):
        module_name = getmodule(self).__name__
        module_name = module_name.replace(".", "_x_")
        self.service = f"{module_name}" + "_x_Test_x_{}_x_<locals>_x_myservice"
        self.args_in = sentinel.arg1, sentinel.arg2
        self.kwargs_in = dict(kwarg1=sentinel.kwarg1, kwarg2=sentinel.kwarg2)

    def test_args_too_many(self):
        emsg = "Invalid lenient service arguments, expecting 1"
        with self.assertRaisesRegex(AssertionError, emsg):
            lenient_service(None, None)

    def test_args_not_callable(self):
        emsg = "Invalid lenient service argument, expecting a callable"
        with self.assertRaisesRegex(AssertionError, emsg):
            lenient_service(None)

    def test_call_naked(self):
        @lenient_service
        def myservice():
            return LENIENT.__dict__.copy()

        qualname_service = self.service.format("test_call_naked")
        state = LENIENT.__dict__
        self.assertIn(qualname_service, state)
        self.assertTrue(state[qualname_service])
        result = myservice()
        self.assertIn(qualname_service, result)
        self.assertTrue(result[qualname_service])

    def test_call_naked_alternative(self):
        def myservice():
            return LENIENT.__dict__.copy()

        qualname_service = self.service.format("test_call_naked_alternative")
        result = lenient_service(myservice)()
        self.assertIn(qualname_service, result)
        self.assertTrue(result[qualname_service])

    def test_call_naked_service_args_kwargs(self):
        @lenient_service
        def myservice(*args, **kwargs):
            return args, kwargs

        args_out, kwargs_out = myservice(*self.args_in, **self.kwargs_in)
        self.assertEqual(args_out, self.args_in)
        self.assertEqual(kwargs_out, self.kwargs_in)

    def test_call_naked_doc(self):
        @lenient_service
        def myservice():
            """myservice doc-string"""

        self.assertEqual(myservice.__doc__, "myservice doc-string")

    def test_call(self):
        @lenient_service()
        def myservice():
            return LENIENT.__dict__.copy()

        qualname_service = self.service.format("test_call")
        state = LENIENT.__dict__
        self.assertIn(qualname_service, state)
        self.assertTrue(state[qualname_service])
        result = myservice()
        self.assertIn(qualname_service, result)
        self.assertTrue(result[qualname_service])

    def test_call_alternative(self):
        def myservice():
            return LENIENT.__dict__.copy()

        qualname_service = self.service.format("test_call_alternative")
        result = (lenient_service())(myservice)()
        self.assertIn(qualname_service, result)
        self.assertTrue(result[qualname_service])

    def test_call_service_args_kwargs(self):
        @lenient_service()
        def myservice(*args, **kwargs):
            return args, kwargs

        args_out, kwargs_out = myservice(*self.args_in, **self.kwargs_in)
        self.assertEqual(args_out, self.args_in)
        self.assertEqual(kwargs_out, self.kwargs_in)

    def test_call_doc(self):
        @lenient_service()
        def myservice():
            """myservice doc-string"""

        self.assertEqual(myservice.__doc__, "myservice doc-string")


if __name__ == "__main__":
    tests.main()
