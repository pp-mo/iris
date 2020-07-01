# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""
Unit tests for the :func:`iris.common.lenient.lenient_client`.

"""

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests

from inspect import getmodule
from unittest.mock import sentinel

from iris.common.lenient import LENIENT, lenient_client


class Test(tests.IrisTest):
    def setUp(self):
        module_name = getmodule(self).__name__
        module_name = module_name.replace(".", "_x_")
        self.client = f"{module_name}" + "_x_Test_x_{}_x_<locals>_x_myclient"
        self.service = f"{module_name}" + "_x_Test_x_{}_x_<locals>_x_myservice"
        self.active = "active"
        self.args_in = sentinel.arg1, sentinel.arg2
        self.kwargs_in = dict(kwarg1=sentinel.kwarg1, kwarg2=sentinel.kwarg2)

    def test_args_too_many(self):
        emsg = "Invalid lenient client arguments, expecting 1"
        with self.assertRaisesRegex(AssertionError, emsg):
            lenient_client(None, None)

    def test_args_not_callable(self):
        emsg = "Invalid lenient client argument, expecting a callable"
        with self.assertRaisesRegex(AssertionError, emsg):
            lenient_client(None)

    def test_args_and_kwargs(self):
        def func():
            pass

        emsg = (
            "Invalid lenient client, got both arguments and keyword arguments"
        )
        with self.assertRaisesRegex(AssertionError, emsg):
            lenient_client(func, services=func)

    def test_call_naked(self):
        @lenient_client
        def myclient():
            return LENIENT.__dict__.copy()

        result = myclient()
        self.assertIn(self.active, result)
        qualname_client = self.client.format("test_call_naked")
        self.assertEqual(result[self.active], qualname_client)
        self.assertNotIn(qualname_client, result)

    def test_call_naked_alternative(self):
        def myclient():
            return LENIENT.__dict__.copy()

        result = lenient_client(myclient)()
        self.assertIn(self.active, result)
        qualname_client = self.client.format("test_call_naked_alternative")
        self.assertEqual(result[self.active], qualname_client)
        self.assertNotIn(qualname_client, result)

    def test_call_naked_client_args_kwargs(self):
        @lenient_client
        def myclient(*args, **kwargs):
            return args, kwargs

        args_out, kwargs_out = myclient(*self.args_in, **self.kwargs_in)
        self.assertEqual(args_out, self.args_in)
        self.assertEqual(kwargs_out, self.kwargs_in)

    def test_call_naked_doc(self):
        @lenient_client
        def myclient():
            """myclient doc-string"""

        self.assertEqual(myclient.__doc__, "myclient doc-string")

    def test_call_no_kwargs(self):
        @lenient_client()
        def myclient():
            return LENIENT.__dict__.copy()

        result = myclient()
        self.assertIn(self.active, result)
        qualname_client = self.client.format("test_call_no_kwargs")
        self.assertEqual(result[self.active], qualname_client)
        self.assertNotIn(qualname_client, result)

    def test_call_no_kwargs_alternative(self):
        def myclient():
            return LENIENT.__dict__.copy()

        result = (lenient_client())(myclient)()
        self.assertIn(self.active, result)
        qualname_client = self.client.format("test_call_no_kwargs_alternative")
        self.assertEqual(result[self.active], qualname_client)
        self.assertNotIn(qualname_client, result)

    def test_call_kwargs_none(self):
        @lenient_client(services=None)
        def myclient():
            return LENIENT.__dict__.copy()

        result = myclient()
        self.assertIn(self.active, result)
        qualname_client = self.client.format("test_call_kwargs_none")
        self.assertEqual(result[self.active], qualname_client)
        self.assertNotIn(qualname_client, result)

    def test_call_kwargs_single(self):
        service = sentinel.service

        @lenient_client(services=service)
        def myclient():
            return LENIENT.__dict__.copy()

        result = myclient()
        self.assertIn(self.active, result)
        qualname_client = self.client.format("test_call_kwargs_single")
        self.assertEqual(result[self.active], qualname_client)
        self.assertIn(qualname_client, result)
        self.assertEqual(result[qualname_client], set([(service, True)]))

    def test_call_kwargs_single_callable(self):
        def myservice():
            pass

        @lenient_client(services=myservice)
        def myclient():
            return LENIENT.__dict__.copy()

        test_name = "test_call_kwargs_single_callable"
        result = myclient()
        self.assertIn(self.active, result)
        qualname_client = self.client.format(test_name)
        self.assertEqual(result[self.active], qualname_client)
        self.assertIn(qualname_client, result)
        qualname_service = self.service.format(test_name)
        self.assertEqual(
            result[qualname_client], set([(qualname_service, True)])
        )

    def test_call_kwargs_iterable(self):
        services = (sentinel.service1, sentinel.service2)

        @lenient_client(services=services)
        def myclient():
            return LENIENT.__dict__.copy()

        result = myclient()
        self.assertIn(self.active, result)
        qualname_client = self.client.format("test_call_kwargs_iterable")
        self.assertEqual(result[self.active], qualname_client)
        self.assertIn(qualname_client, result)
        self.assertEqual(
            result[qualname_client], set((svc, True) for svc in services)
        )

    def test_call_client_args_kwargs(self):
        @lenient_client()
        def myclient(*args, **kwargs):
            return args, kwargs

        args_out, kwargs_out = myclient(*self.args_in, **self.kwargs_in)
        self.assertEqual(args_out, self.args_in)
        self.assertEqual(kwargs_out, self.kwargs_in)

    def test_call_doc(self):
        @lenient_client()
        def myclient():
            """myclient doc-string"""

        self.assertEqual(myclient.__doc__, "myclient doc-string")


if __name__ == "__main__":
    tests.main()
