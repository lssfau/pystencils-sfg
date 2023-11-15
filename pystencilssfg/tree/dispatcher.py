from __future__ import annotations
from typing import Callable, TypeVar, Generic, ParamSpec
from types import MethodType

from functools import wraps

from .basic_nodes import SfgCallTreeNode

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
    return wraps(method)(VisitorDispatcher(method))
