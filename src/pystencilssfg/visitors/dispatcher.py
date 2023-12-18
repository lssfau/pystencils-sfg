from __future__ import annotations
from typing import Callable, TypeVar, Generic, ParamSpec
from types import MethodType

from functools import wraps

V = TypeVar("V")
R = TypeVar("R")


class VisitorDispatcher(Generic[V, R]):
    def __init__(self, wrapped_method: Callable[..., R]):
        self._dispatch_dict: dict[type, Callable[..., R]] = {}
        self._wrapped_method: Callable[..., R] = wrapped_method

    def case(self, node_type: type):
        """Decorator for visitor's case handlers."""

        def decorate(handler: Callable[..., R]):
            if node_type in self._dispatch_dict:
                raise ValueError(f"Duplicate visitor case {node_type}")
            self._dispatch_dict[node_type] = handler
            return handler

        return decorate

    def __call__(self, instance: V, node: object, *args, **kwargs) -> R:
        for cls in node.__class__.mro():
            if cls in self._dispatch_dict:
                return self._dispatch_dict[cls](instance, node, *args, **kwargs)

        return self._wrapped_method(instance, node, *args, **kwargs)

    def __get__(self, obj: V, objtype=None) -> Callable[..., R]:
        if obj is None:
            return self
        return MethodType(self, obj)


def visitor(method):
    """Decorator to create a visitor using type-based dispatch.

    Use this decorator to convert a method into a visitor, like shown below.
    After declaring a method (e.g. `my_method`) a visitor,
    its case handlers can be declared using the `my_method.case` decorator, like this:

    ```Python
    class DemoVisitor:
        @visitor
        def visit(self, obj: object):
            # fallback case
            ...

        @visit.case(str)
        def visit_str(self, obj: str):
            # code for handling a str
    ```

    When `visit` is later called with some object `x`, the case handler to be executed is
    determined according to the method resolution order of `x` (i.e. along its type's inheritance hierarchy).
    If no case matches, the fallback code in the original visitor method is executed.
    In this example, if `visit` is called with an object of type `str`, the call is dispatched to `visit_str`.

    This visitor dispatch method is primarily designed for traversing abstract syntax tree structures.
    The primary visitor method (`visit` in above example) should define the common parent type of all object
    types the visitor can handle, with cases declared for all required subtypes.
    However, this type relationship is not enforced at runtime.
    """
    return wraps(method)(VisitorDispatcher(method))
