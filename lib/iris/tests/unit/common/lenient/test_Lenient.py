# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""
Unit tests for the :class:`iris.common.lenient.Lenient`.

"""

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests

from collections import Iterable

from iris.common.lenient import (
    LENIENT_ENABLE_DEFAULT,
    LENIENT_PROTECTED,
    LENIENT,
    Lenient,
    qualname,
    lenient_client,
)


class Test___init__(tests.IrisTest):
    def setUp(self):
        self.expected = dict(active=None, enable=LENIENT_ENABLE_DEFAULT)

    def test_default(self):
        lenient = Lenient()
        self.assertEqual(self.expected, lenient.__dict__)

    def test_args_service_str(self):
        service = "service1"
        lenient = Lenient(service)
        self.expected.update(dict(service1=True))
        self.assertEqual(self.expected, lenient.__dict__)

    def test_args_services_str(self):
        services = ("service1", "service2")
        lenient = Lenient(*services)
        self.expected.update(dict(service1=True, service2=True))
        self.assertEqual(self.expected, lenient.__dict__)

    def test_args_services_callable(self):
        def service1():
            pass

        def service2():
            pass

        services = (service1, service2)
        lenient = Lenient(*services)
        self.expected.update(
            {qualname(service1): True, qualname(service2): True,}
        )
        self.assertEqual(self.expected, lenient.__dict__)

    def test_kwargs_client_str(self):
        client = dict(client1="service1")
        lenient = Lenient(**client)
        self.expected.update(dict(client1=set([("service1", True)])))
        self.assertEqual(self.expected, lenient.__dict__)

    def test_kwargs_clients_str(self):
        clients = dict(client1="service1", client2="service2")
        lenient = Lenient(**clients)
        self.expected.update(
            dict(
                client1=set([("service1", True)]),
                client2=set([("service2", True)]),
            )
        )
        self.assertEqual(self.expected, lenient.__dict__)

    def test_kwargs_clients_callable(self):
        def client1():
            pass

        def client2():
            pass

        def service1():
            pass

        def service2():
            pass

        qualname_client1 = qualname(client1)
        qualname_client2 = qualname(client2)
        clients = {
            qualname_client1: service1,
            qualname_client2: (service1, service2),
        }
        lenient = Lenient(**clients)
        self.expected.update(
            {
                qualname(client1): set([(qualname(service1), True)]),
                qualname(client2): set(
                    [(qualname(service1), True), (qualname(service2), True)]
                ),
            }
        )
        self.assertEqual(self.expected, lenient.__dict__)


class Test___call__(tests.IrisTest):
    def setUp(self):
        self.client = "myclient"
        self.lenient = Lenient()

    def test_missing_service_str(self):
        self.assertFalse(self.lenient("myservice"))

    def test_missing_service_callable(self):
        def myservice():
            pass

        self.assertFalse(self.lenient(myservice))

    def test_disabled_service_str(self):
        service = "myservice"
        self.lenient.__dict__[service] = False
        self.assertFalse(self.lenient(service))

    def test_disable_service_callable(self):
        def myservice():
            pass

        qualname_service = qualname(myservice)
        self.lenient.__dict__[qualname_service] = False
        self.assertFalse(self.lenient(myservice))

    def test_service_str_with_no_active_client(self):
        service = "myservice"
        self.lenient.__dict__[service] = True
        self.assertFalse(self.lenient(service))

    def test_service_callable_with_no_active_client(self):
        def myservice():
            pass

        qualname_service = qualname(myservice)
        self.lenient.__dict__[qualname_service] = True
        self.assertFalse(self.lenient(myservice))

    def test_service_str_with_active_client_with_no_registered_services(self):
        service = "myservice"
        self.lenient.__dict__[service] = True
        self.lenient.__dict__["active"] = self.client
        self.assertFalse(self.lenient(service))

    def test_service_callable_with_active_client_with_no_registered_services(
        self,
    ):
        def myservice():
            pass

        def myclient():
            pass

        qualname_service = qualname(myservice)
        self.lenient.__dict__[qualname_service] = True
        self.lenient.__dict__["active"] = qualname(myclient)
        self.assertFalse(self.lenient(myservice))

    def test_service_str_with_active_client_with_unmatched_registered_services(
        self,
    ):
        service = "myservice"
        self.lenient.__dict__[service] = True
        self.lenient.__dict__["active"] = self.client
        self.lenient.__dict__[self.client] = set(
            [("service1", True), ("service2", True)]
        )
        self.assertFalse(self.lenient(service))

    def test_service_callable_with_active_client_with_unmatched_registered_services(
        self,
    ):
        def myservice():
            pass

        def myclient():
            pass

        qualname_service = qualname(myservice)
        qualname_client = qualname(myclient)
        self.lenient.__dict__[qualname_service] = True
        self.lenient.__dict__["active"] = qualname_client
        self.lenient.__dict__[qualname_client] = set(
            [("service1", True), ("service2", True)]
        )
        self.assertFalse(self.lenient(myservice))

    def test_service_str_with_active_client_with_registered_services(self):
        service = "myservice"
        self.lenient.__dict__[service] = True
        self.lenient.__dict__["active"] = self.client
        self.lenient.__dict__[self.client] = set(
            [("service1", True), ("service2", True), (service, True),]
        )
        self.assertTrue(self.lenient(service))

    def test_service_callable_with_active_client_with_registered_services(
        self,
    ):
        def myservice():
            pass

        def myclient():
            pass

        qualname_service = qualname(myservice)
        qualname_client = qualname(myclient)
        self.lenient.__dict__[qualname_service] = True
        self.lenient.__dict__["active"] = qualname_client
        self.lenient.__dict__[qualname_client] = set(
            [(qualname_service, True), ("service1", True), ("service2", True),]
        )
        self.assertTrue(self.lenient(myservice))

    def test_service_str_with_active_client_with_unmatched_registered_service_str(
        self,
    ):
        service = "myservice"
        self.lenient.__dict__[service] = True
        self.lenient.__dict__["active"] = self.client
        self.lenient.__dict__[self.client] = set([("serviceXXX", True)])
        self.assertFalse(self.lenient(service))

    def test_service_callable_with_active_client_with_unmatched_registered_service_str(
        self,
    ):
        def myservice():
            pass

        def myclient():
            pass

        qualname_service = qualname(myservice)
        qualname_client = qualname(myclient)
        self.lenient.__dict__[qualname_service] = True
        self.lenient.__dict__["active"] = qualname_client
        self.lenient.__dict__[qualname_client] = set(
            [(f"{qualname_service}XXX", True)]
        )
        self.assertFalse(self.lenient(myservice))

    def test_service_str_with_active_client_with_registered_service_str(self):
        service = "myservice"
        self.lenient.__dict__[service] = True
        self.lenient.__dict__["active"] = self.client
        self.lenient.__dict__[self.client] = set([(service, True)])
        self.assertTrue(self.lenient(service))

    def test_service_callable_with_active_client_with_registered_service_str(
        self,
    ):
        def myservice():
            pass

        def myclient():
            pass

        qualname_service = qualname(myservice)
        qualname_client = qualname(myclient)
        self.lenient.__dict__[qualname_service] = True
        self.lenient.__dict__["active"] = qualname_client
        self.lenient.__dict__[qualname_client] = set(
            [(qualname_service, True)]
        )
        self.assertTrue(self.lenient(myservice))

    def test_enable(self):
        service = "myservice"
        self.lenient.__dict__[service] = True
        self.lenient.__dict__["active"] = self.client
        self.lenient.__dict__[self.client] = set([(service, True)])
        self.assertTrue(self.lenient(service))
        self.lenient.__dict__["enable"] = False
        self.assertFalse(self.lenient(service))


class Test___contains__(tests.IrisTest):
    def setUp(self):
        self.lenient = Lenient()

    def test_in(self):
        self.assertIn("active", self.lenient)

    def test_not_in(self):
        self.assertNotIn("ACTIVATE", self.lenient)


class Test___getattr__(tests.IrisTest):
    def setUp(self):
        self.lenient = Lenient()

    def test_in(self):
        self.assertIsNone(self.lenient.active)

    def test_not_in(self):
        emsg = "Invalid .* option, got 'wibble'."
        with self.assertRaisesRegex(AttributeError, emsg):
            _ = self.lenient.wibble


class Test__getitem__(tests.IrisTest):
    def setUp(self):
        self.lenient = Lenient()

    def test_in(self):
        self.assertIsNone(self.lenient["active"])

    def test_in_callable(self):
        def service():
            pass

        qualname_service = qualname(service)
        self.lenient.__dict__[qualname_service] = True
        self.assertTrue(self.lenient[service])

    def test_not_in(self):
        emsg = "Invalid .* option, got 'wibble'."
        with self.assertRaisesRegex(KeyError, emsg):
            _ = self.lenient["wibble"]

    def test_not_in_callable(self):
        def service():
            pass

        qualname_service = qualname(service)
        emsg = f"Invalid .* option, got '{qualname_service}'."
        with self.assertRaisesRegex(KeyError, emsg):
            _ = self.lenient[service]


class Test___setitem__(tests.IrisTest):
    def setUp(self):
        self.lenient = Lenient()

    def test_not_in(self):
        emsg = "Invalid .* option, got 'wibble'."
        with self.assertRaisesRegex(KeyError, emsg):
            self.lenient["wibble"] = None

    def test_in_value_str(self):
        client = "client"
        service = "service"
        self.lenient.__dict__[client] = None
        self.lenient[client] = service
        self.assertEqual(self.lenient.__dict__[client], (service,))

    def test_callable_in_value_str(self):
        def client():
            pass

        service = "service"
        qualname_client = qualname(client)
        self.lenient.__dict__[qualname_client] = None
        self.lenient[client] = service
        self.assertEqual(self.lenient.__dict__[qualname_client], (service,))

    def test_in_value_callable(self):
        def service():
            pass

        client = "client"
        qualname_service = qualname(service)
        self.lenient.__dict__[client] = None
        self.lenient[client] = service
        self.assertEqual(self.lenient.__dict__[client], (qualname_service,))

    def test_callable_in_value_callable(self):
        def client():
            pass

        def service():
            pass

        qualname_client = qualname(client)
        qualname_service = qualname(service)
        self.lenient.__dict__[qualname_client] = None
        self.lenient[client] = service
        self.assertEqual(
            self.lenient.__dict__[qualname_client], (qualname_service,)
        )

    def test_in_value_bool(self):
        client = "client"
        self.lenient.__dict__[client] = None
        self.lenient[client] = True
        self.assertTrue(self.lenient.__dict__[client])
        self.assertFalse(isinstance(self.lenient.__dict__[client], Iterable))

    def test_callable_in_value_bool(self):
        def client():
            pass

        qualname_client = qualname(client)
        self.lenient.__dict__[qualname_client] = None
        self.lenient[client] = True
        self.assertTrue(self.lenient.__dict__[qualname_client])
        self.assertFalse(
            isinstance(self.lenient.__dict__[qualname_client], Iterable)
        )

    def test_in_value_iterable(self):
        client = "client"
        services = ("service1", "service2")
        self.lenient.__dict__[client] = None
        self.lenient[client] = services
        self.assertEqual(self.lenient.__dict__[client], services)

    def test_callable_in_value_iterable(self):
        def client():
            pass

        qualname_client = qualname(client)
        services = ("service1", "service2")
        self.lenient.__dict__[qualname_client] = None
        self.lenient[client] = services
        self.assertEqual(self.lenient.__dict__[qualname_client], services)

    def test_in_value_iterable_callable(self):
        def service1():
            pass

        def service2():
            pass

        client = "client"
        self.lenient.__dict__[client] = None
        qualname_services = (qualname(service1), qualname(service2))
        self.lenient[client] = (service1, service2)
        self.assertEqual(self.lenient.__dict__[client], qualname_services)

    def test_callable_in_value_iterable_callable(self):
        def client():
            pass

        def service1():
            pass

        def service2():
            pass

        qualname_client = qualname(client)
        self.lenient.__dict__[qualname_client] = None
        qualname_services = (qualname(service1), qualname(service2))
        self.lenient[client] = (service1, service2)
        self.assertEqual(
            self.lenient.__dict__[qualname_client], qualname_services
        )

    def test_active_iterable(self):
        active = "active"
        self.assertIsNone(self.lenient.__dict__[active])
        emsg = "Invalid .* option 'active'"
        with self.assertRaisesRegex(ValueError, emsg):
            self.lenient[active] = (None,)

    def test_active_str(self):
        active = "active"
        client = "client1"
        self.assertIsNone(self.lenient.__dict__[active])
        self.lenient[active] = client
        self.assertEqual(self.lenient.__dict__[active], client)

    def test_active_callable(self):
        def client():
            pass

        active = "active"
        qualname_client = qualname(client)
        self.assertIsNone(self.lenient.__dict__[active])
        self.lenient[active] = client
        self.assertEqual(self.lenient.__dict__[active], qualname_client)

    def test_enable(self):
        enable = "enable"
        self.assertEqual(self.lenient.__dict__[enable], LENIENT_ENABLE_DEFAULT)
        self.lenient[enable] = True
        self.assertTrue(self.lenient.__dict__[enable])
        self.lenient[enable] = False
        self.assertFalse(self.lenient.__dict__[enable])

    def test_enable_invalid(self):
        emsg = "Invalid .* option 'enable'"
        with self.assertRaisesRegex(ValueError, emsg):
            self.lenient["enable"] = None


class Test_context(tests.IrisTest):
    def setUp(self):
        self.lenient = Lenient()
        self.default = dict(active=None, enable=LENIENT_ENABLE_DEFAULT)

    def copy(self):
        return self.lenient.__dict__.copy()

    def test_nop(self):
        pre = self.copy()
        with self.lenient.context():
            context = self.copy()
        post = self.copy()
        self.assertEqual(pre, self.default)
        self.assertEqual(context, self.default)
        self.assertEqual(post, self.default)

    def test_active_str(self):
        client = "client"
        pre = self.copy()
        with self.lenient.context(client):
            context = self.copy()
        post = self.copy()
        self.assertEqual(pre, self.default)
        expected = self.default.copy()
        expected.update(dict(active=client))
        self.assertEqual(context, expected)
        self.assertEqual(post, self.default)

    def test_active_callable(self):
        def client():
            pass

        pre = self.copy()
        with self.lenient.context(client):
            context = self.copy()
        post = self.copy()
        qualname_client = qualname(client)
        self.assertEqual(pre, self.default)
        expected = self.default.copy()
        expected.update(dict(active=qualname_client))
        self.assertEqual(context, expected)
        self.assertEqual(post, self.default)

    def test_args_str(self):
        client = "client"
        services = ("service1", "service2")
        pre = self.copy()
        with self.lenient.context(client, services):
            context = self.copy()
        post = self.copy()
        self.assertEqual(pre, self.default)
        expected = self.default.copy()
        expected.update(
            dict(active=client, client=set((svc, True) for svc in services))
        )
        self.assertEqual(context["active"], expected["active"])
        self.assertEqual(set(context["client"]), set(expected["client"]))
        self.assertEqual(post, self.default)

    def test_args_callable(self):
        def service1():
            pass

        def service2():
            pass

        client = "client"
        services = (service1, service2)
        pre = self.copy()
        with self.lenient.context(client, services):
            context = self.copy()
        post = self.copy()
        qualname_services = tuple([qualname(service) for service in services])
        self.assertEqual(pre, self.default)
        expected = self.default.copy()
        expected.update(
            dict(
                active=client,
                client=set((svc, True) for svc in qualname_services),
            )
        )
        self.assertEqual(context["active"], expected["active"])
        self.assertEqual(context["client"], expected["client"])
        self.assertEqual(post, self.default)

    def test_context_runtime(self):
        services = ("service1", "service2")
        pre = self.copy()
        with self.lenient.context(active=None, services=services):
            context = self.copy()
        post = self.copy()
        self.assertEqual(pre, self.default)
        expected = self.default.copy()
        expected.update(
            dict(
                active="__context",
                __context=set([(srv, True) for srv in services]),
            )
        )
        self.assertEqual(context, expected)
        self.assertEqual(post, self.default)


class Test_context2__newstyles(tests.IrisTest):
    def setUp(self):
        self.lenient = Lenient()
        self.default = dict(active=None, enable=LENIENT_ENABLE_DEFAULT)

    def copy(self):
        return self.lenient.__dict__.copy()

    def test_service_keys(self):
        client = "client"
        services = ("service1", "service2")
        pre = self.copy()
        with self.lenient.context(client, service1=True, service2=True):
            context = self.copy()
        post = self.copy()
        self.assertEqual(pre, self.default)
        expected = self.default.copy()
        expected.update(
            dict(active=client, client=set((svc, True) for svc in services))
        )
        self.assertEqual(context["active"], expected["active"])
        self.assertEqual(set(context["client"]), set(expected["client"]))
        self.assertEqual(post, self.default)

    def test_setting_false(self):
        def service1():
            pass

        def service2():
            pass

        qualname1, qualname2 = [qualname(svc) for svc in (service1, service2)]
        pre = self.copy()

        # Note: use dict for the keywords, as qualnames are really long !
        settings = {qualname1: True, qualname2: False}

        with self.lenient.context("client", **settings):
            context = self.copy()
        post = self.copy()
        self.assertEqual(pre, self.default)
        expected = self.default.copy()
        expected.update(
            dict(
                active="client",
                client=set([(qualname1, True), (qualname2, False)]),
            )
        )
        self.assertEqual(context["active"], expected["active"])
        self.assertEqual(context["client"], expected["client"])
        self.assertEqual(post, self.default)

    def test_setting_nonbinary(self):
        service_names = ("svc1", "svc2", "svc3", "svc4")

        def service_values():
            return [LENIENT("svc" + str(ix)) for ix in range(1, 5)]

        pre = self.copy()

        client_settings = dict(svc1=True, svc2=False, svc3="seven", svc4=-5.3)

        @lenient_client(services=client_settings)
        def client():
            return service_values()

        client_qualname = qualname(client)

        for name in service_names:
            LENIENT.register_service(name)

        svcs_noclient = service_values()
        svcs_inclient = client()
        with self.lenient.context(client, **client_settings):
            context = self.copy()

        post = self.copy()
        self.assertEqual(pre, self.default)
        expected = self.default.copy()
        expected.update(
            dict(
                active=client_qualname,
                client=set(
                    [
                        ("svc1", True),
                        ("svc2", False),
                        ("svc3", "seven"),
                        ("svc4", -5.3),
                    ]
                ),
            )
        )
        self.assertEqual(context["active"], expected["active"])
        self.assertEqual(context[client_qualname], expected["client"])
        self.assertEqual(post, self.default)
        self.assertEqual(svcs_noclient, [False, False, False, False])
        self.assertEqual(svcs_inclient, [True, False, "seven", -5.3])

    def test_setting_modify(self):
        pre = self.copy()

        with self.lenient.context("client", set1=1, set2=2):
            context1 = self.copy()
            with self.lenient.context(
                "client", set2="not two", modify_existing=True
            ):
                context2 = self.copy()
        post = self.copy()
        self.assertEqual(pre, self.default)
        expected1 = self.default.copy()
        expected1.update(
            dict(active="client", client=set([("set1", 1), ("set2", 2)]),)
        )
        self.assertEqual(context1["active"], "client")
        self.assertEqual(context1["client"], expected1["client"])
        self.assertEqual(post, self.default)
        expected2 = self.default.copy()
        expected2.update(
            dict(
                active="client",
                client=set([("set1", 1), ("set2", "not two")]),
            )
        )
        self.assertEqual(context2["active"], "client")
        self.assertEqual(context2["client"], expected2["client"])
        self.assertEqual(post, self.default)


class Test_enable(tests.IrisTest):
    def setUp(self):
        self.lenient = Lenient()

    def test_getter(self):
        self.assertEqual(self.lenient.enable, LENIENT_ENABLE_DEFAULT)

    def test_setter_invalid(self):
        emsg = "Invalid .* option 'enable'"
        with self.assertRaisesRegex(ValueError, emsg):
            self.lenient.enable = 0

    def test_setter(self):
        self.assertEqual(self.lenient.enable, LENIENT_ENABLE_DEFAULT)
        self.lenient.enable = False
        self.assertFalse(self.lenient.enable)


class Test_register_client(tests.IrisTest):
    def setUp(self):
        self.lenient = Lenient()

    def test_not_protected(self):
        emsg = "Cannot register .* protected non-client"
        for protected in LENIENT_PROTECTED:
            with self.assertRaisesRegex(ValueError, emsg):
                self.lenient.register_client(protected, "service")

    def test_str_service_str(self):
        client = "client"
        service = "service"
        self.lenient.register_client(client, service)
        self.assertIn(client, self.lenient.__dict__)
        self.assertEqual(self.lenient.__dict__[client], set([(service, True)]))

    def test_str_services_str(self):
        client = "client"
        services = ("service1", "service2")
        self.lenient.register_client(client, services)
        self.assertIn(client, self.lenient.__dict__)
        self.assertEqual(
            self.lenient.__dict__[client], set((srv, True) for srv in services)
        )

    def test_callable_service_callable(self):
        def client():
            pass

        def service():
            pass

        qualname_client = qualname(client)
        qualname_service = qualname(service)
        self.lenient.register_client(client, service)
        self.assertIn(qualname_client, self.lenient.__dict__)
        self.assertEqual(
            self.lenient.__dict__[qualname_client],
            set([(qualname_service, True)]),
        )

    def test_callable_services_callable(self):
        def client():
            pass

        def service1():
            pass

        def service2():
            pass

        qualname_client = qualname(client)
        qualname_services = (qualname(service1), qualname(service2))
        self.lenient.register_client(client, (service1, service2))
        self.assertIn(qualname_client, self.lenient.__dict__)
        self.assertEqual(
            self.lenient.__dict__[qualname_client],
            set((srv, True) for srv in qualname_services),
        )

    def test_services_empty(self):
        emsg = "Require at least one .* lenient client service."
        with self.assertRaisesRegex(ValueError, emsg):
            self.lenient.register_client("client", ())

    def test_services_overwrite(self):
        client = "client"
        services = ("service1", "service2")
        self.lenient.__dict__[client] = services
        self.assertEqual(self.lenient[client], services)
        new_services = ("service3", "service4")
        self.lenient.register_client(client, services=new_services)
        self.assertEqual(
            self.lenient[client], set((srv, True) for srv in new_services)
        )

    def test_services_append(self):
        client = "client"
        services = ("service1", "service2")  # old style
        services_set = set((srv, True) for srv in services)
        self.lenient.__dict__[client] = services_set
        self.assertEqual(self.lenient[client], services_set)
        new_services = ("service3", "service4")
        self.lenient.register_client(
            client, services=new_services, append=True
        )
        expected = set((srv, True) for srv in services + new_services)
        self.assertEqual(set(self.lenient[client]), expected)


class Test_register_service(tests.IrisTest):
    def setUp(self):
        self.lenient = Lenient()

    def test_str(self):
        service = "service"
        self.assertNotIn(service, self.lenient.__dict__)
        self.lenient.register_service(service)
        self.assertIn(service, self.lenient.__dict__)
        self.assertFalse(isinstance(self.lenient.__dict__[service], Iterable))
        self.assertTrue(self.lenient.__dict__[service])

    def test_callable(self):
        def service():
            pass

        qualname_service = qualname(service)
        self.assertNotIn(qualname_service, self.lenient.__dict__)
        self.lenient.register_service(service)
        self.assertIn(qualname_service, self.lenient.__dict__)
        self.assertFalse(
            isinstance(self.lenient.__dict__[qualname_service], Iterable)
        )
        self.assertTrue(self.lenient.__dict__[qualname_service])

    def test_not_protected(self):
        emsg = "Cannot register .* protected non-service"
        for protected in LENIENT_PROTECTED:
            self.lenient.__dict__[protected] = None
            with self.assertRaisesRegex(ValueError, emsg):
                self.lenient.register_service("active")


class Test_unregister_client(tests.IrisTest):
    def setUp(self):
        self.lenient = Lenient()

    def test_not_protected(self):
        emsg = "Cannot unregister .* protected non-client"
        for protected in LENIENT_PROTECTED:
            self.lenient.__dict__[protected] = None
            with self.assertRaisesRegex(ValueError, emsg):
                self.lenient.unregister_client(protected)

    def test_not_in(self):
        emsg = "Cannot unregister unknown .* client"
        with self.assertRaisesRegex(ValueError, emsg):
            self.lenient.unregister_client("client")

    def test_not_client(self):
        client = "client"
        self.lenient.__dict__[client] = True
        emsg = "Cannot unregister .* non-client"
        with self.assertRaisesRegex(ValueError, emsg):
            self.lenient.unregister_client(client)

    def test_not_client_callable(self):
        def client():
            pass

        qualname_client = qualname(client)
        self.lenient.__dict__[qualname_client] = True
        emsg = "Cannot unregister .* non-client"
        with self.assertRaisesRegex(ValueError, emsg):
            self.lenient.unregister_client(client)

    def test_str(self):
        client = "client"
        self.lenient.__dict__[client] = (None,)
        self.lenient.unregister_client(client)
        self.assertNotIn(client, self.lenient.__dict__)

    def test_callable(self):
        def client():
            pass

        qualname_client = qualname(client)
        self.lenient.__dict__[qualname_client] = (None,)
        self.lenient.unregister_client(client)
        self.assertNotIn(qualname_client, self.lenient.__dict__)


class Test_unregister_service(tests.IrisTest):
    def setUp(self):
        self.lenient = Lenient()

    def test_not_protected(self):
        emsg = "Cannot unregister .* protected non-service"
        for protected in LENIENT_PROTECTED:
            self.lenient.__dict__[protected] = None
            with self.assertRaisesRegex(ValueError, emsg):
                self.lenient.unregister_service(protected)

    def test_not_in(self):
        emsg = "Cannot unregister unknown .* service"
        with self.assertRaisesRegex(ValueError, emsg):
            self.lenient.unregister_service("service")

    def test_not_service(self):
        service = "service"
        self.lenient.__dict__[service] = (None,)
        emsg = "Cannot unregister .* non-service"
        with self.assertRaisesRegex(ValueError, emsg):
            self.lenient.unregister_service(service)

    def test_not_service_callable(self):
        def service():
            pass

        qualname_service = qualname(service)
        self.lenient.__dict__[qualname_service] = (None,)
        emsg = "Cannot unregister .* non-service"
        with self.assertRaisesRegex(ValueError, emsg):
            self.lenient.unregister_service(service)

    def test_str(self):
        service = "service"
        self.lenient.__dict__[service] = True
        self.lenient.unregister_service(service)
        self.assertNotIn(service, self.lenient.__dict__)

    def test_callable(self):
        def service():
            pass

        qualname_service = qualname(service)
        self.lenient.__dict__[qualname_service] = True
        self.lenient.unregister_service(service)
        self.assertNotIn(qualname_service, self.lenient.__dict__)


if __name__ == "__main__":
    tests.main()
