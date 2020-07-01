# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.

from collections.abc import Iterable
from contextlib import contextmanager
from copy import deepcopy
from functools import wraps
from inspect import getmodule
import threading


__all__ = [
    "LENIENT",
    "Lenient",
    "lenient_client",
    "lenient_service",
    "qualname",
]


#: Default Lenient services global activation state.
LENIENT_ENABLE_DEFAULT = True

#: Protected Lenient internal non-client, non-service keys.
LENIENT_PROTECTED = ("active", "enable")


def lenient_client(*dargs, services=None):
    """
    Decorator that allows a client function/method to declare at runtime that
    it is executing and requires lenient behaviour from a prior registered
    lenient service function/method.

    This decorator supports being called with no arguments e.g.,

        @lenient_client()
        def func():
            pass

    This is equivalent to using it as a simple naked decorator e.g.,

        @lenient_client
        def func()
            pass

    Alternatively, this decorator supports the lenient client explicitly
    declaring the lenient services that it wishes to use e.g.,

        @lenient_client(services=(service1, service2, ...)
        def func():
            pass

    Args:

    * dargs (tuple of callable):
        A tuple containing the callable lenient client function/method to be
        wrapped by the decorator. This is automatically populated by Python
        through the decorator interface. No argument requires to be manually
        provided.

    Kwargs:

    * services (callable or str or iterable of callable/str)
        Zero or more function/methods, or equivalent fully qualified string names, of
        lenient service function/methods.

    Returns:
        Closure wrapped function/method.

    """
    ndargs = len(dargs)

    if ndargs:
        assert (
            ndargs == 1
        ), f"Invalid lenient client arguments, expecting 1 got {ndargs}."
        assert callable(
            dargs[0]
        ), "Invalid lenient client argument, expecting a callable."

    assert not (
        ndargs and services
    ), "Invalid lenient client, got both arguments and keyword arguments."

    if ndargs:
        # The decorator has been used as a simple naked decorator.
        (func,) = dargs

        @wraps(func)
        def lenient_client_inner_naked(*args, **kwargs):
            """
            Closure wrapper function to register the wrapped function/method
            as active at runtime before executing it.

            """
            with LENIENT.context(active=qualname(func)):
                result = func(*args, **kwargs)
            return result

        result = lenient_client_inner_naked
    else:
        # The decorator has been called with None, zero or more explicit lenient services.
        if services is None:
            services = ()

        if isinstance(services, str) or not isinstance(services, Iterable):
            services = (services,)

        def lenient_client_outer(func):
            @wraps(func)
            def lenient_client_inner(*args, **kwargs):
                """
                Closure wrapper function to register the wrapped function/method
                as active at runtime before executing it.

                """
                with LENIENT.context(qualname(func), services):
                    result = func(*args, **kwargs)
                return result

            return lenient_client_inner

        result = lenient_client_outer

    return result


def lenient_service(*dargs):
    """
    Decorator that allows a function/method to declare that it supports lenient
    behaviour as a service.

    Registration is at Python interpreter parse time.

    The decorator supports being called with no arguments e.g.,

        @lenient_service()
        def func():
            pass

    This is equivalent to using it as a simple naked decorator e.g.,

        @lenient_service
        def func():
            pass

    Args:

    * dargs (tuple of callable):
        A tuple containing the callable lenient service function/method to be
        wrapped by the decorator. This is automatically populated by Python
        through the decorator interface. No argument requires to be manually
        provided.

    Returns:
        Closure wrapped function/method.

    """
    ndargs = len(dargs)

    if ndargs:
        assert (
            ndargs == 1
        ), f"Invalid lenient service arguments, expecting 1 got {ndargs}."
        assert callable(
            dargs[0]
        ), "Invalid lenient service argument, expecting a callable."

    if ndargs:
        # The decorator has been used as a simple naked decorator.
        # Thus the (single) argument is a function to be wrapped.
        # We just register the argument function as a lenient service, and
        # return it unchanged
        (func,) = dargs

        LENIENT.register_service(func)

        # This decorator registers 'func': the func itself is unchanged.
        result = func

    else:
        # The decorator has been called with no arguments.
        # Return a decorator, to apply to 'func' immediately following.
        def lenient_service_outer(func):
            LENIENT.register_service(func)

            # Decorator registers 'func', but func itself is unchanged.
            return func

        result = lenient_service_outer

    return result


def qualname(func):
    """
    Return the fully qualified function/method string name.

    Args:

    * func (callable):
        Callable function/method. Non-callable arguments are simply
        passed through.

    .. note::
        Inherited methods will be qualified with the base class that
        defines the method.

    """
    result = func
    if callable(func):
        module = getmodule(func)
        result = f"{module.__name__}.{func.__qualname__}"
        result = result.replace(".", "_x_")
    return result


class Lenient(threading.local):
    def __init__(self, *args, **kwargs):
        """
        A container for managing the run-time lenient services and client
        options for pre-defined functions/methods.

        Args:

        * args (callable or str or iterable of callable/str)
            A function/method or fully qualified string name of the function/method
            acting as a lenient service.

        Kwargs:

        * kwargs (dict of callable/str or iterable of callable/str)
            Mapping of lenient client function/method, or fully qualified sting name
            of the function/method, to one or more lenient service
            function/methods or fully qualified string name of function/methods.

        For example::

            Lenient(service1, service2, client1=service1, client2=(service1, service2))

        Note that, the values of these options are thread-specific.

        """
        # The executing lenient client at runtime.
        self.__dict__["active"] = None
        # The global lenient services state activation switch.
        self.__dict__["enable"] = LENIENT_ENABLE_DEFAULT

        for service in args:
            self.register_service(service)

        for client, services in kwargs.items():
            self.register_client(client, services)

    def __call__(self, func):
        """
        Determine whether it is valid for the function/method to provide a
        lenient service at runtime to the actively executing lenient client.

        Args:

        * func (callable or str):
            A function/method or fully qualified string name of the function/method.

        Returns:
            Boolean.

        """
        result = False
        if self.__dict__["enable"]:
            service = qualname(func)
            if service in self and self.__dict__[service]:
                active = self.__dict__["active"]
                if active is not None and active in self:
                    services = self.__dict__[active]
                    found = [val for svc, val in services if svc == service]
                    result = found[0] if found else False
        return result

    def __contains__(self, name):
        return name in self.__dict__

    def __getattr__(self, name):
        if name not in self.__dict__:
            cls = self.__class__.__name__
            emsg = f"Invalid {cls!r} option, got {name!r}."
            raise AttributeError(emsg)
        return self.__dict__[name]

    def __getitem__(self, name):
        name = qualname(name)
        if name not in self.__dict__:
            cls = self.__class__.__name__
            emsg = f"Invalid {cls!r} option, got {name!r}."
            raise KeyError(emsg)
        return self.__dict__[name]

    def __repr__(self):
        cls = self.__class__.__name__
        width = len(cls) + 1
        kwargs = [
            "{}={!r}".format(name, self.__dict__[name])
            for name in sorted(self.__dict__.keys())
        ]
        joiner = ",\n{}".format(" " * width)
        return "{}({})".format(cls, joiner.join(kwargs))

    def __setitem__(self, name, value):
        name = qualname(name)
        cls = self.__class__.__name__

        if name not in self.__dict__:
            emsg = f"Invalid {cls!r} option, got {name!r}."
            raise KeyError(emsg)

        if name == "active":
            value = qualname(value)
            if not isinstance(value, str) and value is not None:
                emsg = f"Invalid {cls!r} option {name!r}, got {value!r}."
                raise ValueError(emsg)
            self.__dict__[name] = value
        elif name == "enable":
            self.enable = value
        else:
            if isinstance(value, str) or callable(value):
                value = (value,)
            if isinstance(value, Iterable):
                value = tuple([qualname(item) for item in value])
            self.__dict__[name] = value

    @staticmethod
    def _services_asdict(services):
        # Convert list of services, or dict(service:value) to dictionary form.
        # For lists, also accepts callables, converting to qualnames.
        if services is None:
            services = {}
        elif isinstance(services, str) or not isinstance(services, Iterable):
            services = [services]

        if hasattr(services, "items"):
            # Dictionary form contains setting values e.g. {'x':1, 'y':2}.
            services = {
                qualname(service): value for service, value in services.items()
            }
        else:
            # List form (x, y) is equivalent to {x:True. y:True}
            services = {qualname(service): True for service in services}

        return services

    @contextmanager
    def context(
        self,
        active=None,
        services=None,
        enable=None,
        modify_existing=False,
        **service_values_dict,
    ):
        """
        Return a context manager which allows temporary modification of
        the lenient option state for the active thread.

        For example::
            with iris.LENIENT.context(client, (srv1, srv2)):
                # ... code that expects some lenient behaviour

            with iris.LENIENT.context(client, srv1=True, srv2=True):
                # ... code that expects some lenient behaviour

            with iris.LENIENT.context(client, srv2=False, modify_existing=True):
                # ... code that amends for some NON-lenient behaviour

            with iris.LENIENT.context(client, set1=3, set3='adjust'):
                # ... code using non-binary settings.

        """

        def update_client(client, services):
            if client in self.__dict__:
                # Convert existing set of pairs to dict
                new_services = {svc: val for svc, val in self.__dict__[client]}
            else:
                new_services = {}

            # Update dict with new settings.
            if not hasattr(services, "keys"):
                services = {svc: True for svc in services}
            new_services.update(services)

            # Save back, as a set-of-pairs.
            self.__dict__[client] = set(
                (svc, val) for svc, val in new_services.items()
            )

        # Save the original state.
        original_state = deepcopy(self.__dict__)

        # First update the state with the fixed keyword controls.
        if active is not None:
            self.active = qualname(active)
        if enable is not None:
            self.enable = enable

        # Get the active client.
        active = self.__dict__["active"]

        if services or service_values_dict:
            # Update the client with the provided services.
            new_services = self._services_asdict(services)
            new_services.update(self._services_asdict(service_values_dict))

            if active is None:
                # Ensure not to use "context" as the ephemeral name
                # of the context manager runtime "active" lenient client,
                # as this causes a namespace clash with this method
                # i.e., Lenient.context, via Lenient.__getattr__
                active = "__context"
                self.active = active

            update_client(active, new_services)

        else:
            # Append previous ephemeral services (for non-specific client) to the active client.
            if (
                active is not None
                and active != "__context"
                and "__context" in self.__dict__
            ):
                new_services = self.__context
                update_client(active, new_services)

        try:
            yield
        finally:
            # Restore the original state.
            self.__dict__.clear()
            self.__dict__.update(original_state)

    @property
    def enable(self):
        """Return the activation state of the lenient services."""
        return self.__dict__["enable"]

    @enable.setter
    def enable(self, state):
        """
        Set the activate state of the lenient services.

        Setting the state to `False` disables all lenient services, and
        setting the state to `True` enables all lenient services.

        Args:

        * state (bool):
            Activate state for lenient services.

        """
        if not isinstance(state, bool):
            cls = self.__class__.__name__
            emsg = f"Invalid {cls!r} option 'enable', got {state!r}."
            raise ValueError(emsg)
        self.__dict__["enable"] = state

    def register_client(self, client, services, append=False):
        """
        Add the provided mapping of lenient client function/method to
        required lenient service function/methods.

        Args:

        * client (callable or str):
            A client function/method or fully qualified string name of the
            client function/method.

        * services (callable or str or iterable of callable/str):
            One or more service function/methods or fully qualified string names
            of the required service function/method.

        Kwargs:

        * append (bool):
            If True, append the lenient services to any pre-registered lenient
            services for the provided lenient client. Default is False.

        """
        client = qualname(client)
        cls = self.__class__.__name__

        if client in LENIENT_PROTECTED:
            emsg = f"Cannot register {cls!r} protected non-client, got {client!r}."
            raise ValueError(emsg)

        services = self._services_asdict(services)
        if not services:
            emsg = f"Require at least one {cls!r} lenient client service."
            raise ValueError(emsg)

        if append:
            # Service order is not significant, therefore there is no
            # requirement to preserve it.
            existing = self.__dict__[client] if client in self else ()
            updated = dict(existing)
            updated.update(services)
            services = updated

        # Convert dictionary to a set of pairs.
        services = set((svc, services[svc]) for svc in sorted(services.keys()))
        # N.B. must be in standard order??
        self.__dict__[client] = services

    def register_service(self, func):
        """
        Add the provided function/method as providing a lenient service and
        activate it.

        Args:

        * func (callable or str):
            A service function/method or fully qualified string name of the
            service function/method.

        """
        func = qualname(func)
        if func in LENIENT_PROTECTED:
            cls = self.__class__.__name__
            emsg = (
                f"Cannot register {cls!r} protected non-service, got {func!r}."
            )
            raise ValueError(emsg)
        self.__dict__[func] = True

    def unregister_client(self, func):
        """
        Remove the provided function/method as a lenient client using lenient services.

        Args:

        * func (callable or str):
            A function/method of fully qualified string name of the function/method.

        """
        func = qualname(func)
        cls = self.__class__.__name__

        if func in LENIENT_PROTECTED:
            emsg = f"Cannot unregister {cls!r} protected non-client, got {func!r}."
            raise ValueError(emsg)

        if func in self.__dict__:
            value = self.__dict__[func]
            if isinstance(value, bool):
                emsg = f"Cannot unregister {cls!r} non-client, got {func!r}."
                raise ValueError(emsg)
            del self.__dict__[func]
        else:
            emsg = f"Cannot unregister unknown {cls!r} client, got {func!r}."
            raise ValueError(emsg)

    def unregister_service(self, func):
        """
        Remove the provided function/method as providing a lenient service.

        Args:

        * func (callable or str):
            A function/method or fully qualified string name of the function/method.

        """
        func = qualname(func)
        cls = self.__class__.__name__

        if func in LENIENT_PROTECTED:
            emsg = f"Cannot unregister {cls!r} protected non-service, got {func!r}."
            raise ValueError(emsg)

        if func in self.__dict__:
            value = self.__dict__[func]
            if not isinstance(value, bool):
                emsg = f"Cannot unregister {cls!r} non-service, got {func!r}."
                raise ValueError(emsg)
            del self.__dict__[func]
        else:
            emsg = f"Cannot unregister unknown {cls!r} service, got {func!r}."
            raise ValueError(emsg)


#: Instance that manages all Iris run-time lenient client and service options.
LENIENT = Lenient()
