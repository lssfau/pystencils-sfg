from __future__ import annotations
from typing import Iterable
from itertools import chain
from abc import ABC, abstractmethod

from pystencils.types import PsType

from ..ir.source_components import SfgVar, SfgHeaderInclude
from ..exceptions import SfgException


class DependentExpression:
    __match_args__ = ("expr", "depends")

    def __init__(self, expr: str, depends: Iterable[SfgVar | AugExpr]):
        self._expr: str = expr
        deps: set[SfgVar] = set()
        for obj in depends:
            if isinstance(obj, AugExpr):
                deps |= obj.depends
            else:
                deps.add(obj)

        self._depends = tuple(deps)

    @property
    def expr(self) -> str:
        return self._expr

    @property
    def depends(self) -> set[SfgVar]:
        return set(self._depends)

    def __hash_contents__(self):
        return (self._expr, self._depends)

    def __eq__(self, other: object):
        if not isinstance(other, DependentExpression):
            return False

        return self.__hash_contents__() == other.__hash_contents__()

    def __hash__(self):
        return hash(self.__hash_contents__())

    def __str__(self) -> str:
        return self.expr

    def __add__(self, other: DependentExpression):
        return DependentExpression(self.expr + other.expr, self.depends | other.depends)


class AugExpr:
    def __init__(self, dtype: PsType | None = None):
        self._dtype = dtype
        self._bound: DependentExpression | None = None

    def var(self, name: str):
        v = SfgVar(name, self.get_dtype(), self.required_includes)
        expr = DependentExpression(name, (v,))
        return self._bind(expr)

    @staticmethod
    def make(code: str, depends: Iterable[SfgVar | AugExpr]):
        return AugExpr()._bind(DependentExpression(code, depends))

    @staticmethod
    def format(fmt: str, *deps, **kwdeps) -> AugExpr:
        return AugExpr().bind(fmt, *deps, **kwdeps)

    def bind(self, fmt: str, *deps, **kwdeps):
        depends = filter(
            lambda obj: isinstance(obj, (SfgVar, AugExpr)), chain(deps, kwdeps.values())
        )
        code = fmt.format(*deps, **kwdeps)
        self._bind(DependentExpression(code, depends))
        return self

    def expr(self) -> DependentExpression:
        if self._bound is None:
            raise SfgException("No syntax bound to this AugExpr.")

        return self._bound

    @property
    def depends(self) -> set[SfgVar]:
        if self._bound is None:
            raise SfgException("No syntax bound to this AugExpr.")

        return self._bound.depends

    @property
    def dtype(self) -> PsType | None:
        return self._dtype

    def get_dtype(self) -> PsType:
        if self._dtype is None:
            raise SfgException("This AugExpr has no known data type.")

        return self._dtype

    @property
    def required_includes(self) -> set[SfgHeaderInclude]:
        return set()

    def __str__(self) -> str:
        if self._bound is None:
            return "/* [ERROR] unbound AugExpr */"
        else:
            return str(self._bound)

    def _bind(self, expr: DependentExpression):
        if self._bound is not None:
            raise SfgException("Attempting to bind an already-bound AugExpr.")

        self._bound = expr
        return self

    def _is_bound(self) -> bool:
        return self._bound is not None


class IFieldExtraction(ABC):
    """Interface for objects defining how to extract low-level field parameters
    from high-level data structures."""

    @abstractmethod
    def ptr(self) -> AugExpr:
        pass

    @abstractmethod
    def size(self, coordinate: int) -> AugExpr | None:
        pass

    @abstractmethod
    def stride(self, coordinate: int) -> AugExpr | None:
        pass


class SrcField(AugExpr):
    """Represents a C++ data structure that can be mapped to a *pystencils* field."""

    @abstractmethod
    def get_extraction(self) -> IFieldExtraction:
        pass


class SrcVector(AugExpr, ABC):
    """Represents a C++ data structure that represents a mathematical vector."""

    @abstractmethod
    def extract_component(self, coordinate: int) -> AugExpr:
        pass
