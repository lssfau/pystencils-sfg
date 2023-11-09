from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .context import SfgContext
    
from .tree import SfgCallTreeNode, SfgSequence
from .tree.visitors import FlattenSequences, ParameterCollector

class SfgFunction:
    def __init__(self, ctx: SfgContext, name: str, tree: SfgCallTreeNode):
        self._ctx = ctx
        self._name = name
        self._tree = tree
        
        flattener = FlattenSequences()
        flattener.visit(self._tree)
        
        param_collector = ParameterCollector()
        self._parameters = param_collector.visit(self._tree)

    @property
    def name(self):
        return self._name

    @property
    def parameters(self):
        return self._parameters

    def get_code(self):
        return self._tree.get_code(self._ctx)

