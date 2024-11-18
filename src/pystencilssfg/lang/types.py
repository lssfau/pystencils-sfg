from typing import Any
from pystencils.types import PsType, PsPointerType


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
