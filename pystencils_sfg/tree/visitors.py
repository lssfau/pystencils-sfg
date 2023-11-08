from typing import Set
from functools import reduce

from pystencils.typing import TypedSymbol

from .basic_nodes import SfgCallTreeNode, SfgCallTreeLeaf, SfgSequence


class ParameterCollector():
    def visit(self, node: SfgCallTreeNode) -> Set[TypedSymbol]:
        if isinstance(node, SfgCallTreeLeaf):
            return self._visit_SfgCallTreeLeaf(node)
        elif isinstance(node, SfgSequence):
            return self._visit_SfgSequence(node)
        else:
            return self._visit_branchingNode(node)

    def _visit_SfgCallTreeLeaf(self, leaf: SfgCallTreeLeaf) -> Set[TypedSymbol]:
        return leaf.required_symbols

    def _visit_SfgSequence(self, sequence: SfgSequence) -> Set[TypedSymbol]:
        """
            Only in a sequence may parameters be defined and visible to subsequent nodes.
        """
        
        params = set()
        for c in sequence.children[::-1]:
            if isinstance(c, SfgCallTreeLeaf):
                #   Only a leaf in a sequence may effectively define symbols
                #   Remove these from the required parameters
                params -= c.defined_symbols
            
            params |= self.visit(c)
        return params

    def _visit_branchingNode(self, node: SfgCallTreeNode):
        """
            Each interior node that is not a sequence simply requires the union of all parameters
            required by its children.
        """
        return reduce(lambda x, y: x | y, (self.visit(c) for c in node.children), set())
