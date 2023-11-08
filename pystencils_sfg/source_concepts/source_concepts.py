from typing import Optional
from abc import ABC, abstractmethod
from pystencils import TypedSymbol

class SrcClass:
    def __init__(self):
        pass


class SrcObject(ABC):
    def __init__(self, src_type, identifier: Optional[str]):
        self._src_type = src_type
        self._identifier = identifier

    @property
    def _sfg_symbol(self):
        return TypedSymbol(self._identifier, self._src_type)
    

class SrcMemberAccess():
    def __init__(self, obj: SrcObject, code_string: str):
        self._obj = obj
        self._code_string = code_string

    def _sfg_code_string():
        return self._code_string

