from typing import Any, Iterable
from abc import ABC
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


class CppType(PsCustomType, ABC):
    includes: frozenset[HeaderFile]

    @property
    def required_headers(self) -> set[str]:
        return set(str(h) for h in self.includes)


def cpptype(typestr: str, include: str | HeaderFile | Iterable[str | HeaderFile] = ()):
    headers: list[str | HeaderFile]

    if isinstance(include, (str, HeaderFile)):
        headers = [
            include,
        ]
    else:
        headers = list(include)

    def _fixarg(template_arg):
        if isinstance(template_arg, PsType):
            return template_arg.c_string()
        else:
            return str(template_arg)

    class TypeClass(CppType):
        includes = frozenset(HeaderFile.parse(h) for h in headers)

        def __init__(self, *template_args, const: bool = False, **template_kwargs):
            template_args = tuple(_fixarg(arg) for arg in template_args)
            template_kwargs = {
                key: _fixarg(value) for key, value in template_kwargs.items()
            }

            name = typestr.format(*template_args, **template_kwargs)
            super().__init__(name, const)

    return TypeClass


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
