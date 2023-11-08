from abc import ABC, abstractmethod

from .source_concepts import SrcObject, SrcMemberAccess

class SrcContiguousContainer(SrcObject):
    def __init__(self, src_type, identifier: Optional[str]):
        super().__init__(src_type, identifier)

    @abstractmethod
    def ptr(self) -> SrcMemberAccess:
        pass

    @abstractmethod
    def size(self, dimension: int) -> SrcMemberAccess:
        pass

    @abstractmethod
    def stride(self, dimension: int) -> SrcMemberAccess:
        pass

