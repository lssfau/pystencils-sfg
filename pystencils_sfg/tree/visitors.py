from typing import Set
from functools import reduce

from pystencils.typing import TypedSymbol

from .basic_nodes import SfgCallTreeNode, SfgCallTreeLeaf, SfgSequence, SfgParameterDefinition


class FlattenSequences():
    """Flattens any nested sequences occuring in a kernel call tree."""
    def visit(self, node: SfgCallTreeNode) -> None:
        if isinstance(node, SfgSequence):
            return self._visit_SfgSequence(node)
        else:
            for c in node.children:
                self.visit(c)

    def _visit_SfgSequence(self, sequence: SfgSequence) -> None:
        children_flattened = []
        
        def flatten(seq: SfgSequence):
            for c in seq.children:
                if isinstance(c, SfgSequence):
                    flatten(c)
                else:
                    children_flattened.append(c)
        
        flatten(sequence)

        for c in children_flattened:
            self.visit(c)

        sequence._children = children_flattened


class ParameterCollector():
    """Collects all parameters required but not defined in a kernel call tree.

    Requires that all sequences in the tree are flattened.
    """
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
            if isinstance(c, SfgParameterDefinitionNode):
                params -= c.defined_symbols
            
            assert not isinstance(c, SfgSequence), "Sequence not flattened."
            params |= self.visit(c)
        return params

    def _visit_branchingNode(self, node: SfgCallTreeNode):
        """
            Each interior node that is not a sequence simply requires the union of all parameters
            required by its children.
        """
        return reduce(lambda x, y: x | y, (self.visit(c) for c in node.children), set())
