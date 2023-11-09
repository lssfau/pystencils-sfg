from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Sequence, Union, Set

if TYPE_CHECKING:
    from ..source_components import SfgHeaderInclude

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
    def required_includes(self) -> Set[SfgHeaderInclude]:
        return set()

    @property
    def typed_symbol(self):
        return TypedSymbol(self._identifier, self._src_type)
