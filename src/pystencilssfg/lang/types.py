from __future__ import annotations
from typing import Any, Iterable, Sequence, Mapping, TypeVar, Generic
from abc import ABC
from dataclasses import dataclass
from itertools import chain

import string

from pystencils.types import PsType, PsPointerType, PsCustomType
from .headers import HeaderFile


class VoidType(PsType):
    """C++ void type."""

    def __init__(self, const: bool = False):
        super().__init__(False)

    def __args__(self) -> tuple[Any, ...]:
        return ()

    def c_string(self) -> str:
        return "void"

    def __repr__(self) -> str:
        return "VoidType()"


void = VoidType()


class _TemplateArgFormatter(string.Formatter):

    def format_field(self, arg, format_spec):
        if isinstance(arg, PsType):
            arg = arg.c_string()
        return super().format_field(arg, format_spec)

    def check_unused_args(
        self, used_args: set[int | str], args: Sequence, kwargs: Mapping[str, Any]
    ) -> None:
        max_args_len: int = (
            max((k for k in used_args if isinstance(k, int)), default=-1) + 1
        )
        if len(args) > max_args_len:
            raise ValueError(
                f"Too many positional arguments: Expected {max_args_len}, but got {len(args)}"
            )

        extra_keys = set(kwargs.keys()) - used_args  # type: ignore
        if extra_keys:
            raise ValueError(f"Extraneous keyword arguments: {extra_keys}")


@dataclass(frozen=True)
class _TemplateArgs:
    pargs: tuple[Any, ...]
    kwargs: tuple[tuple[str, Any], ...]


class CppType(PsCustomType, ABC):
    class_includes: frozenset[HeaderFile]
    template_string: str

    def __init__(self, *template_args, const: bool = False, **template_kwargs):
        #   Support for cloning CppTypes
        if template_args and isinstance(template_args[0], _TemplateArgs):
            assert not template_kwargs
            targs = template_args[0]
            pargs = targs.pargs
            kwargs = dict(targs.kwargs)
        else:
            pargs = template_args
            kwargs = template_kwargs
            targs = _TemplateArgs(
                pargs, tuple(sorted(kwargs.items(), key=lambda t: t[0]))
            )

        formatter = _TemplateArgFormatter()
        name = formatter.format(self.template_string, *pargs, **kwargs)

        self._targs = targs
        self._includes = self.class_includes

        for arg in chain(pargs, kwargs.values()):
            match arg:
                case CppType():
                    self._includes |= arg.includes
                case PsType():
                    self._includes |= {
                        HeaderFile.parse(h) for h in arg.required_headers
                    }

        super().__init__(name, const=const)

    def __args__(self) -> tuple[Any, ...]:
        return (self._targs,)

    @property
    def includes(self) -> frozenset[HeaderFile]:
        return self._includes

    @property
    def required_headers(self) -> set[str]:
        return set(str(h) for h in self.class_includes)


TypeClass_T = TypeVar("TypeClass_T", bound=CppType)
"""Python type variable bound to `CppType`."""


class CppTypeFactory(Generic[TypeClass_T]):
    """Type Factory returned by `cpptype`."""

    def __init__(self, tclass: type[TypeClass_T]) -> None:
        self._type_class = tclass

    @property
    def includes(self) -> frozenset[HeaderFile]:
        """Set of headers required by this factory's type"""
        return self._type_class.class_includes

    @property
    def template_string(self) -> str:
        """Template string of this factory's type"""
        return self._type_class.template_string

    def __str__(self) -> str:
        return f"Factory for {self.template_string}` defined in {self.includes}"

    def __repr__(self) -> str:
        return f"CppTypeFactory({self.template_string}, includes={{ {', '.join(str(i) for i in self.includes)} }})"

    def __call__(self, *args, ref: bool = False, **kwargs) -> TypeClass_T | Ref:
        """Create a type object of this factory's C++ type template.

        Args:
            args, kwargs: Positional and keyword arguments are forwarded to the template string formatter
            ref: If ``True``, return a reference type

        Returns:
            An instantiated type object
        """

        obj = self._type_class(*args, **kwargs)
        if ref:
            return Ref(obj)
        else:
            return obj


def cpptype(
    template_str: str, include: str | HeaderFile | Iterable[str | HeaderFile] = ()
) -> CppTypeFactory:
    """Describe a C++ type template, associated with a set of required header files.

    This function allows users to define C++ type templates using
    `Python format string syntax <https://docs.python.org/3/library/string.html#formatstrings>`_.
    The types may furthermore be annotated with a set of header files that must be included
    in order to use the type.

    >>> opt_template = lang.cpptype("std::optional< {T} >", "<optional>")
    >>> opt_template.template_string
    'std::optional< {T} >'

    This function returns a `CppTypeFactory` object, which in turn can be called to create
    an instance of the C++ type template.
    Therein, the ``template_str`` argument is treated as a Python format string:
    The positional and keyword arguments passed to the returned type factory are passed
    through machinery that is based on `str.format` to produce the actual type name.

    >>> int_option = opt_template(T="int")
    >>> int_option.c_string().strip()
    'std::optional< int >'

    The factory may also create reference types when the ``ref=True`` is specified.

    >>> int_option_ref = opt_template(T="int", ref=True)
    >>> int_option_ref.c_string().strip()
    'std::optional< int >&'

    Args:
        template_str: Format string defining the type template
        include: Either the name of a header file, or a sequence of names of header files

    Returns:
        CppTypeFactory: A factory used to instantiate the type template
    """
    headers: list[str | HeaderFile]

    if isinstance(include, (str, HeaderFile)):
        headers = [
            include,
        ]
    else:
        headers = list(include)

    class TypeClass(CppType):
        template_string = template_str
        class_includes = frozenset(HeaderFile.parse(h) for h in headers)

    return CppTypeFactory[TypeClass](TypeClass)


class Ref(PsType):
    """C++ reference type."""

    __match_args__ = "base_type"

    def __init__(self, base_type: PsType, const: bool = False):
        super().__init__(False)
        self._base_type = base_type

    def __args__(self) -> tuple[Any, ...]:
        return (self.base_type,)

    @property
    def base_type(self) -> PsType:
        return self._base_type

    def c_string(self) -> str:
        base_str = self.base_type.c_string()
        return base_str + "&"

    def __repr__(self) -> str:
        return f"Ref({repr(self.base_type)})"


def strip_ptr_ref(dtype: PsType):
    match dtype:
        case Ref():
            return strip_ptr_ref(dtype.base_type)
        case PsPointerType():
            return strip_ptr_ref(dtype.base_type)
        case _:
            return dtype
