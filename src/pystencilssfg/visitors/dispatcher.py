from __future__ import annotations
from typing import Callable, TypeVar, Generic, ParamSpec
from types import MethodType

from functools import wraps

from ..tree.basic_nodes import SfgCallTreeNode

V = TypeVar("V")
R = TypeVar("R")
P = ParamSpec("P")


class VisitorDispatcher(Generic[V, R]):
    def __init__(self, wrapped_method: Callable[..., R]):
        self._dispatch_dict: dict[type, Callable[..., R]] = {}
        self._wrapped_method: Callable[..., R] = wrapped_method

    def case(self, node_type: type):
        """Decorator for visitor's methods"""

        def decorate(handler: Callable[..., R]):
            if node_type in self._dispatch_dict:
                raise ValueError(f"Duplicate visitor case {node_type}")
            self._dispatch_dict[node_type] = handler
            return handler

        return decorate

    def __call__(self, instance: V, node: SfgCallTreeNode, *args, **kwargs) -> R:
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
    After declaring a method `<method-name>` a visitor,
    its dispatch variants can be declared using the `<method-name>,case` decarator, like this:

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

    Now, if `visit` is called with an object of type `str`, the call is dispatched to `visit_str`.
    Dispatch follows the Python method resolution order; if cases are declared for both a type
    and some of its parent types, the most specific case is executed.
    If no case matches, the fallback code in the original `visit` method is executed.

    This visitor dispatch method is primarily designed for traversing abstract syntax tree structures.
    The primary visitor method (`visit` in above example) defines the common parent type of all object
    types the visitor can handle - every case's type must be a subtype of this.
    Of course, like in the example, this visitor dispatcher may be used with arbitrary types if the base
    type is `object`.
    """
    return wraps(method)(VisitorDispatcher(method))
