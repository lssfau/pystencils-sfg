from typing import Optional

from ..source_concepts import SrcMemberAccess
from ..containers import SrcContiguousContainer

class std_mdspan(SrcContiguousContainer):
    def __init__(self, identifer: str):
        super().__init__("std::mdspan", identifier)

    def ptr(self):
        return SrcMemberAccess(self, f"{self._identifier}.data_handle()")

    def size(self, dimension: int):
        return SrcMemberAccess(self, f"{self._identifier}.extents().extent({dimension})")

    def stride(self, dimension: int):
        return SrcMemberAccess(self, f"{self._identifier}.stride({dimension})")
