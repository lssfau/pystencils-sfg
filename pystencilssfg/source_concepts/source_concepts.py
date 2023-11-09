from __future__ import annotations

from typing import Optional, Sequence, Union, Set
from abc import ABC
from pystencils import TypedSymbol

class SrcObject(ABC):
    def __init__(self, src_type, identifier: Optional[str]):
        self._src_type = src_type
        self._identifier = identifier

    @property
    def src_type(self):
        return self._src_type
    
    @property
    def identifier(self):
        return self._identifier

    @property
    def typed_symbol(self):
        return TypedSymbol(self._identifier, self._src_type)



    

# class SrcExpression(SrcStatements):
#     """Represents a single expression of the source language, e.g. a C++ expression 
#     (c.f. https://en.cppreference.com/w/cpp/language/expressions).

#     It is the user's responsibility to ensure that the code string is valid code in the output language,
#     and that the list of required  objects is complete.

#     Args:
#         code_string: Code to be printed out.
#         required_objects: Objects (as `SrcObject` or `TypedSymbol`) that are required as input to this expression.
#     """

#     def __init__(self,
#                  code_string: str,
#                  required_objects: Sequence[Union[SrcObject, TypedSymbol]]):
#         super().__init__(code_string, (), required_objects)
