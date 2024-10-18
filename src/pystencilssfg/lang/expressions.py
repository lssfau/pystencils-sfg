from __future__ import annotations
from typing import Iterable, TypeAlias, Any, TYPE_CHECKING
from itertools import chain
from abc import ABC, abstractmethod

import sympy as sp

from pystencils import TypedSymbol
from pystencils.types import PsType, UserTypeSpec, create_type

from ..exceptions import SfgException

if TYPE_CHECKING:
    from ..ir.source_components import SfgHeaderInclude


__all__ = [
    "SfgVar",
    "AugExpr",
    "VarLike",
    "ExprLike",
    "asvar",
    "depends",
    "IFieldExtraction",
    "SrcField",
    "SrcVector",
]


class SfgVar:
    """C++ Variable.

    Args:
        name: Name of the variable. Must be a valid C++ identifer.
        dtype: Data type of the variable.
    """

    __match_args__ = ("name", "dtype")

    def __init__(
        self,
        name: str,
        dtype: UserTypeSpec,
        required_includes: set[SfgHeaderInclude] | None = None,
    ):
        #   TODO: Replace `required_includes` by using a property
        #   Includes attached this way may currently easily be lost during postprocessing,
        #   since they are not part of `_args`
        self._name = name
        self._dtype = create_type(dtype)

        self._required_includes = (
            required_includes if required_includes is not None else set()
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def dtype(self) -> PsType:
        return self._dtype

    def _args(self) -> tuple[Any, ...]:
        return (self._name, self._dtype)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SfgVar):
            return False

        return self._args() == other._args()

    def __hash__(self) -> int:
        return hash(self._args())

    @property
    def required_includes(self) -> set[SfgHeaderInclude]:
        return self._required_includes

    def name_and_type(self) -> str:
        return f"{self._name}: {self._dtype}"

    def __str__(self) -> str:
        return self._name

    def __repr__(self) -> str:
        return self.name_and_type()


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


class VarExpr(DependentExpression):
    def __init__(self, var: SfgVar):
        self._var = var
        super().__init__(var.name, (var,))

    @property
    def variable(self) -> SfgVar:
        return self._var


class AugExpr:
    """C++ expression augmented with variable dependencies and a type-dependent interface.

    `AugExpr` is the primary class for modelling C++ expressions in *pystencils-sfg*.
    It stores both an expression's code string and the set of variables (`SfgVar`)
    the expression depends on. This dependency information is used by the postprocessing
    system to infer function parameter lists.

    In addition, subclasses of `AugExpr` can mimic C++ APIs by defining factory methods that
    build expressions for C++ method calls, etc., from a list of argument expressions.

    Args:
        dtype: Optional, data type of this expression interface
    """

    __match_args__ = ("expr", "dtype")

    def __init__(self, dtype: UserTypeSpec | None = None):
        self._dtype = create_type(dtype) if dtype is not None else None
        self._bound: DependentExpression | None = None
        self._is_variable = False

    def var(self, name: str):
        v = SfgVar(name, self.get_dtype(), self.required_includes)
        expr = VarExpr(v)
        return self._bind(expr)

    @staticmethod
    def make(code: str, depends: Iterable[SfgVar | AugExpr]):
        return AugExpr()._bind(DependentExpression(code, depends))

    @staticmethod
    def format(fmt: str, *deps, **kwdeps) -> AugExpr:
        """Create a new `AugExpr` by combining existing expressions."""
        return AugExpr().bind(fmt, *deps, **kwdeps)

    def bind(self, fmt: str, *deps, **kwdeps):
        dependencies: set[SfgVar] = set()

        from pystencils.sympyextensions import is_constant

        for expr in chain(deps, kwdeps.values()):
            if isinstance(expr, _ExprLike):
                dependencies |= depends(expr)
            elif isinstance(expr, sp.Expr) and not is_constant(expr):
                raise ValueError(
                    f"Cannot parse SymPy expression as C++ expression: {expr}\n"
                    "  * pystencils-sfg is currently unable to parse non-constant SymPy expressions "
                    "since they contain symbols without type information."
                )

        code = fmt.format(*deps, **kwdeps)
        self._bind(DependentExpression(code, dependencies))
        return self

    def expr(self) -> DependentExpression:
        if self._bound is None:
            raise SfgException("No syntax bound to this AugExpr.")

        return self._bound

    @property
    def code(self) -> str:
        if self._bound is None:
            raise SfgException("No syntax bound to this AugExpr.")
        return str(self._bound)

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
    def is_variable(self) -> bool:
        return isinstance(self._bound, VarExpr)

    def as_variable(self) -> SfgVar:
        if not isinstance(self._bound, VarExpr):
            raise SfgException("This expression is not a variable")
        return self._bound.variable

    @property
    def required_includes(self) -> set[SfgHeaderInclude]:
        return set()

    def __str__(self) -> str:
        if self._bound is None:
            return "/* [ERROR] unbound AugExpr */"
        else:
            return str(self._bound)

    def __repr__(self) -> str:
        return str(self)

    def _bind(self, expr: DependentExpression):
        if self._bound is not None:
            raise SfgException("Attempting to bind an already-bound AugExpr.")

        self._bound = expr
        return self

    def _is_bound(self) -> bool:
        return self._bound is not None


_VarLike = (AugExpr, SfgVar, TypedSymbol)
VarLike: TypeAlias = AugExpr | SfgVar | TypedSymbol
"""Things that may act as a variable.

Variable-like objects are entities from pystencils and pystencils-sfg that define
a variable name and data type.
Any `VarLike` object can be transformed into a canonical representation (i.e. `SfgVar`)
using `asvar`.
"""


_ExprLike = (str, AugExpr, SfgVar, TypedSymbol)
ExprLike: TypeAlias = str | AugExpr | SfgVar | TypedSymbol
"""Things that may act as a C++ expression.

This type combines all objects that *pystencils-sfg* can handle in the place of C++
expressions. These include all valid variable types (`VarLike`), plain strings, and
complex expressions with variable dependency information (`AugExpr`).

The set of variables an expression depends on can be determined using `depends`.
"""


def asvar(var: VarLike) -> SfgVar:
    """Cast a variable-like object to its canonical representation,

    Args:
        var: Variable-like object

    Returns:
        SfgVar: Variable cast as `SfgVar`.

    Raises:
        ValueError: If given a non-variable `AugExpr`,
            a `TypedSymbol` with a `DynamicType`,
            or any non-variable-like object.
    """
    match var:
        case SfgVar():
            return var
        case AugExpr():
            return var.as_variable()
        case TypedSymbol():
            from pystencils import DynamicType

            if isinstance(var.dtype, DynamicType):
                raise ValueError(
                    f"Unable to cast dynamically typed symbol {var} to a variable.\n"
                    f"{var} has dynamic type {var.dtype}, which cannot be resolved to a type outside of a kernel."
                )

            return SfgVar(var.name, var.dtype)
        case _:
            raise ValueError(f"Invalid variable: {var}")


def depends(expr: ExprLike) -> set[SfgVar]:
    """Determine the set of variables an expression depends on.

    Args:
        expr: Expression-like object to examine

    Returns:
        set[SfgVar]: Set of variables the expression depends on

    Raises:
        ValueError: If the argument was not a valid expression
    """

    match expr:
        case None | str():
            return set()
        case SfgVar():
            return {expr}
        case TypedSymbol():
            return {asvar(expr)}
        case AugExpr():
            return expr.depends
        case _:
            raise ValueError(f"Invalid expression: {expr}")


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
    """Represents a C++ data structure that can be mapped to a *pystencils* field.

    Args:
        dtype: Data type of the field data structure
    """

    @abstractmethod
    def get_extraction(self) -> IFieldExtraction:
        pass


class SrcVector(AugExpr, ABC):
    """Represents a C++ data structure that represents a mathematical vector.

    Args:
        dtype: Data type of the vector data structure
    """

    @abstractmethod
    def extract_component(self, coordinate: int) -> AugExpr:
        pass
