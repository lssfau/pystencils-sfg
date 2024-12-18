from __future__ import annotations
from typing import Iterable, TypeAlias, Any
from itertools import chain
from abc import ABC, abstractmethod

import sympy as sp

from pystencils import TypedSymbol
from pystencils.types import PsType, UserTypeSpec, create_type

from ..exceptions import SfgException
from .headers import HeaderFile
from .types import strip_ptr_ref, CppType

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
    ):
        self._name = name
        self._dtype = create_type(dtype)

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

    def name_and_type(self) -> str:
        return f"{self._name}: {self._dtype}"

    def __str__(self) -> str:
        return self._name

    def __repr__(self) -> str:
        return self.name_and_type()


class DependentExpression:
    """Wrapper around a C++ expression code string,
    annotated with a set of variables and a set of header files this expression depends on.

    Args:
        expr: C++ Code string of the expression
        depends: Iterable of variables and/or `AugExpr`s from which variable and header dependencies are collected
        includes: Iterable of header files which this expression additionally depends on
    """

    __match_args__ = ("expr", "depends")

    def __init__(
        self,
        expr: str,
        depends: Iterable[SfgVar | AugExpr],
        includes: Iterable[HeaderFile] | None = None,
    ):
        self._expr: str = expr
        deps: set[SfgVar] = set()
        incls: set[HeaderFile] = set(includes) if includes is not None else set()

        for obj in depends:
            if isinstance(obj, AugExpr):
                deps |= obj.depends
                incls |= obj.includes
            else:
                deps.add(obj)

        self._depends = frozenset(deps)
        self._includes = frozenset(incls)

    @property
    def expr(self) -> str:
        return self._expr

    @property
    def depends(self) -> frozenset[SfgVar]:
        return self._depends

    @property
    def includes(self) -> frozenset[HeaderFile]:
        return self._includes

    def __hash_contents__(self):
        return (self._expr, self._depends, self._includes)

    def __eq__(self, other: object):
        if not isinstance(other, DependentExpression):
            return False

        return self.__hash_contents__() == other.__hash_contents__()

    def __hash__(self):
        return hash(self.__hash_contents__())

    def __str__(self) -> str:
        return self.expr

    def __add__(self, other: DependentExpression):
        return DependentExpression(
            self.expr + other.expr,
            self.depends | other.depends,
            self._includes | other._includes,
        )


class VarExpr(DependentExpression):
    def __init__(self, var: SfgVar):
        self._var = var
        base_type = strip_ptr_ref(var.dtype)
        incls: Iterable[HeaderFile]
        match base_type:
            case CppType():
                incls = base_type.includes
            case _:
                incls = (
                    HeaderFile.parse(header) for header in var.dtype.required_headers
                )
        super().__init__(var.name, (var,), incls)

    @property
    def variable(self) -> SfgVar:
        return self._var


class AugExpr:
    """C++ expression augmented with variable dependencies and a type-dependent interface.

    `AugExpr` is the primary class for modelling C++ expressions in *pystencils-sfg*.
    It stores both an expression's code string,
    the set of variables (`SfgVar`) the expression depends on,
    as well as any headers that must be included for the expression to be evaluated.
    This dependency information is used by the composer and postprocessing system
    to infer function parameter lists and automatic header inclusions.

    **Construction and Binding**

    Constructing an `AugExpr` is a two-step process comprising *construction* and *binding*.
    An `AugExpr` can be constructed with our without an associated data type.
    After construction, the `AugExpr` object is still *unbound*;
    it does not yet hold any syntax.

    Syntax binding can happen in two ways:

    - Calling `var <AugExpr.var>` on an unbound `AugExpr` turns it into a *variable* with the given name.
      This variable expression takes its set of required header files from the
      `required_headers <pystencils.types.PsType.required_headers>` field of the data type of the `AugExpr`.
    - Using `bind <AugExpr.bind>`, an unbound `AugExpr` can be bound to an arbitrary string
      of code. The `bind` method mirrors the interface of `str.format` to combine sub-expressions
      and collect their dependencies.
      The `format <AugExpr.format>` static method is a wrapper around `bind` for expressions
      without a type.

    An `AugExpr` can be bound only once.

    **C++ API Mirroring**

    Subclasses of `AugExpr` can mimic C++ APIs by defining factory methods that
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
        """Bind an unbound `AugExpr` instance as a new variable of given name."""
        v = SfgVar(name, self.get_dtype())
        expr = VarExpr(v)
        return self._bind(expr)

    @staticmethod
    def make(code: str, depends: Iterable[SfgVar | AugExpr]):
        return AugExpr()._bind(DependentExpression(code, depends))

    @staticmethod
    def format(fmt: str, *deps, **kwdeps) -> AugExpr:
        """Create a new `AugExpr` by combining existing expressions."""
        return AugExpr().bind(fmt, *deps, **kwdeps)

    def bind(self, fmt: str | AugExpr, *deps, **kwdeps):
        """Bind an unbound `AugExpr` instance to an expression."""
        if isinstance(fmt, AugExpr):
            if bool(deps) or bool(kwdeps):
                raise ValueError(
                    "Binding to another AugExpr does not permit additional arguments"
                )
            if fmt._bound is None:
                raise ValueError("Cannot rebind to unbound AugExpr.")
            self._bind(fmt._bound)
        else:
            dependencies: set[SfgVar] = set()
            incls: set[HeaderFile] = set()

            from pystencils.sympyextensions import is_constant

            for expr in chain(deps, kwdeps.values()):
                if isinstance(expr, _ExprLike):
                    dependencies |= depends(expr)
                    incls |= includes(expr)
                elif isinstance(expr, sp.Expr) and not is_constant(expr):
                    raise ValueError(
                        f"Cannot parse SymPy expression as C++ expression: {expr}\n"
                        "  * pystencils-sfg is currently unable to parse non-constant SymPy expressions "
                        "since they contain symbols without type information."
                    )

            code = fmt.format(*deps, **kwdeps)
            self._bind(DependentExpression(code, dependencies, incls))
        return self

    @property
    def code(self) -> str:
        if self._bound is None:
            raise SfgException("No syntax bound to this AugExpr.")
        return str(self._bound)

    @property
    def depends(self) -> frozenset[SfgVar]:
        if self._bound is None:
            raise SfgException("No syntax bound to this AugExpr.")

        return self._bound.depends

    @property
    def includes(self) -> frozenset[HeaderFile]:
        if self._bound is None:
            raise SfgException("No syntax bound to this AugExpr.")

        return self._bound.includes

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

    def is_bound(self) -> bool:
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
            a `TypedSymbol <pystencils.TypedSymbol>`
            with a `DynamicType <pystencils.sympyextensions.typed_sympy.DynamicType>`,
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
            return set(expr.depends)
        case _:
            raise ValueError(f"Invalid expression: {expr}")


def includes(expr: ExprLike) -> set[HeaderFile]:
    """Determine the set of header files an expression depends on.

    Args:
        expr: Expression-like object to examine

    Returns:
        set[HeaderFile]: Set of headers the expression depends on

    Raises:
        ValueError: If the argument was not a valid variable or expression
    """

    match expr:
        case SfgVar(_, dtype):
            return set(HeaderFile.parse(h) for h in dtype.required_headers)
        case TypedSymbol():
            return includes(asvar(expr))
        case str():
            return set()
        case AugExpr():
            return set(expr.includes)
        case _:
            raise ValueError(f"Invalid expression: {expr}")


class IFieldExtraction(ABC):
    """Interface for objects defining how to extract low-level field parameters
    from high-level data structures."""

    @abstractmethod
    def ptr(self) -> AugExpr:
        ...

    @abstractmethod
    def size(self, coordinate: int) -> AugExpr | None:
        ...

    @abstractmethod
    def stride(self, coordinate: int) -> AugExpr | None:
        ...


class SrcField(AugExpr):
    """Represents a C++ data structure that can be mapped to a *pystencils* field.

    Args:
        dtype: Data type of the field data structure
    """

    @abstractmethod
    def get_extraction(self) -> IFieldExtraction:
        ...


class SrcVector(AugExpr, ABC):
    """Represents a C++ data structure that represents a mathematical vector.

    Args:
        dtype: Data type of the vector data structure
    """

    @abstractmethod
    def extract_component(self, coordinate: int) -> AugExpr:
        ...
