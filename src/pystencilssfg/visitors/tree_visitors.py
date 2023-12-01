from __future__ import annotations

# from typing import TYPE_CHECKING

from functools import reduce

from ..tree.basic_nodes import (
    SfgCallTreeNode,
    SfgCallTreeLeaf,
    SfgSequence,
    SfgStatements,
)
from ..tree.deferred_nodes import SfgParamCollectionDeferredNode
from .dispatcher import visitor
from ..source_concepts.source_objects import TypedSymbolOrObject


class FlattenSequences:
    """Flattens any nested sequences occuring in a kernel call tree."""

    @visitor
    def visit(self, node: SfgCallTreeNode) -> None:
        for c in node.children:
            self.visit(c)

    @visit.case(SfgSequence)
    def sequence(self, sequence: SfgSequence) -> None:
        children_flattened: list[SfgCallTreeNode] = []

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


class ExpandingParameterCollector:
    """Collects all parameters required but not defined in a kernel call tree.
    Expands any deferred nodes of type `SfgParamCollectionDeferredNode` found within sequences on the way.
    """

    def __init__(self) -> None:
        self._flattener = FlattenSequences()

    @visitor
    def visit(self, node: SfgCallTreeNode) -> set[TypedSymbolOrObject]:
        return self.branching_node(node)

    @visit.case(SfgCallTreeLeaf)
    def leaf(self, leaf: SfgCallTreeLeaf) -> set[TypedSymbolOrObject]:
        return leaf.required_parameters

    @visit.case(SfgSequence)
    def sequence(self, sequence: SfgSequence) -> set[TypedSymbolOrObject]:
        """
        Only in a sequence may parameters be defined and visible to subsequent nodes.
        """

        params: set[TypedSymbolOrObject] = set()

        def iter_nested_sequences(
            seq: SfgSequence, visible_params: set[TypedSymbolOrObject]
        ):
            for i in range(len(seq.children) - 1, -1, -1):
                c = seq.children[i]

                if isinstance(c, SfgParamCollectionDeferredNode):
                    c = c.expand(visible_params=visible_params)
                    seq[i] = c

                if isinstance(c, SfgSequence):
                    iter_nested_sequences(c, visible_params)
                else:
                    if isinstance(c, SfgStatements):
                        visible_params -= c.defined_parameters

                    visible_params |= self.visit(c)

        iter_nested_sequences(sequence, params)

        return params

    def branching_node(self, node: SfgCallTreeNode) -> set[TypedSymbolOrObject]:
        """
        Each interior node that is not a sequence simply requires the union of all parameters
        required by its children.
        """
        return reduce(lambda x, y: x | y, (self.visit(c) for c in node.children), set())


class ParameterCollector:
    """Collects all parameters required but not defined in a kernel call tree.

    Requires that all sequences in the tree are flattened.
    """

    @visitor
    def visit(self, node: SfgCallTreeNode) -> set[TypedSymbolOrObject]:
        return self.branching_node(node)

    @visit.case(SfgCallTreeLeaf)
    def leaf(self, leaf: SfgCallTreeLeaf) -> set[TypedSymbolOrObject]:
        return leaf.required_parameters

    @visit.case(SfgSequence)
    def sequence(self, sequence: SfgSequence) -> set[TypedSymbolOrObject]:
        """
        Only in a sequence may parameters be defined and visible to subsequent nodes.
        """

        params: set[TypedSymbolOrObject] = set()
        for c in sequence.children[::-1]:
            if isinstance(c, SfgStatements):
                params -= c.defined_parameters

            assert not isinstance(c, SfgSequence), "Sequence not flattened."
            params |= self.visit(c)
        return params

    def branching_node(self, node: SfgCallTreeNode) -> set[TypedSymbolOrObject]:
        """
        Each interior node that is not a sequence simply requires the union of all parameters
        required by its children.
        """
        return reduce(lambda x, y: x | y, (self.visit(c) for c in node.children), set())
