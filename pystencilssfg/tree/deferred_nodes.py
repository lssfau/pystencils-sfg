from __future__ import annotations
from typing import TYPE_CHECKING, Set

if TYPE_CHECKING:
    from ..context import SfgContext

from abc import ABC, abstractmethod

from pystencils import Field, TypedSymbol
from pystencils.typing import FieldPointerSymbol, FieldShapeSymbol, FieldStrideSymbol

from ..exceptions import SfgException

from .basic_nodes import SfgCallTreeNode
from .builders import make_sequence

from ..source_concepts import SrcField


class SfgDeferredNode(SfgCallTreeNode, ABC):
    """Nodes of this type are inserted as placeholders into the kernel call tree
    and need to be expanded at a later time.

    Subclasses of SfgDeferredNode correspond to nodes that cannot be created yet
    because information required for their construction is not yet known.
    """

    class InvalidAccess:
        def __get__(self):
            raise SfgException("Invalid access into deferred node; deferred nodes must be expanded first.")

    def __init__(self):
        self._children = SfgDeferredNode.InvalidAccess

    get_code = InvalidAccess

    @abstractmethod
    def expand(self, ctx: SfgContext, *args, **kwargs) -> SfgCallTreeNode:
        pass


class SfgParamCollectionDeferredNode(SfgDeferredNode, ABC):
    @abstractmethod
    def expand(self, ctx: SfgContext, visible_params: Set[TypedSymbol]) -> SfgCallTreeNode:
        pass


class SfgDeferredFieldMapping(SfgParamCollectionDeferredNode):
    def __init__(self, field: Field, src_field: SrcField):
        self._field = field
        self._src_field = src_field

    def expand(self, ctx: SfgContext, visible_params: Set[TypedSymbol]) -> SfgCallTreeNode:
        #    Find field pointer
        ptr = None
        for param in visible_params:
            if isinstance(param, FieldPointerSymbol) and param.field_name == self._field.name:
                if param.dtype.base_type != self._field.dtype:
                    raise SfgException("Data type mismatch between field and encountered pointer symbol")
                ptr = param

        #   Find required sizes
        shape = []
        for c, s in enumerate(self._field.shape):
            if isinstance(s, FieldShapeSymbol) and s not in visible_params:
                continue
            else:
                shape.append((c, s))

        #   Find required strides
        strides = []
        for c, s in enumerate(self._field.strides):
            if isinstance(s, FieldStrideSymbol) and s not in visible_params:
                continue
            else:
                strides.append((c, s))

        return make_sequence(
            self._src_field.extract_ptr(ptr),
            *(self._src_field.extract_size(c, s) for c, s in shape),
            *(self._src_field.extract_stride(c, s) for c, s in strides)
        )
