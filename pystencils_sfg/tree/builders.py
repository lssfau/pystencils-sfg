from __future__ import annotations
from typing import TYPE_CHECKING, Any, Sequence

if TYPE_CHECKING:
    from ..context import SfgContext

from abc import ABC, abstractmethod
from .basic_nodes import SfgCallTreeNode, SfgSequence, SfgBlock, SfgCustomStatement
from .conditional import SfgCondition, SfgCustomCondition, SfgBranch
    
class SfgNodeBuilder(ABC):
    def __init__(self, ctx: SfgContext) -> None:
        self._ctx = ctx

    @abstractmethod
    def resolve(self) -> SfgCallTreeNode:
        pass

class SfgSequencer:
    def __init__(self, ctx: SfgContext) -> None:
        self._ctx = ctx

    def __call__(self, *args) -> SfgSequence:
        children = []
        for i, arg in enumerate(args):
            if isinstance(arg, SfgNodeBuilder):
                children.append(arg.resolve())
            elif isinstance(arg, SfgCallTreeNode):
                children.append(arg)
            elif isinstance(arg, str):
                children.append(SfgCustomStatement(arg))
            elif isinstance(arg, tuple):
                #   Tuples are treated as blocks
                subseq = self(*arg)
                children.append(SfgBlock(subseq))
            else:
                raise TypeError(f"Sequence argument {i} has invalid type.")
        
        return SfgSequence(children)
    

class SfgBranchBuilder(SfgNodeBuilder):
    def __init__(self, ctx: SfgContext) -> None:
        super().__init__(ctx)
        self._phase = 0

        self._cond = None
        self._branch_true = SfgSequence(())
        self._branch_false = None

    def __call__(self, *args) -> SfgBranchBuilder:
        match self._phase:
            case 0: # Condition
                if len(args) != 1:
                    raise ValueError("Must specify exactly one argument as branch condition!")
                
                cond = args[0]
                
                if isinstance(cond, str):
                    cond = SfgCustomCondition(cond)
                elif not isinstance(cond, SfgCondition):
                    raise ValueError("Invalid type for branch condition. Must be either `str` or a subclass of `SfgCondition`.")
                
                self._cond = cond

            case 1: # Then-branch
                self._branch_true = self._ctx.seq(*args)
            case 2: # Else-branch
                self._branch_false = self._ctx.seq(*args)
            case _: # There's not third branch!
                raise TypeError("Branch construct already complete.")

        self._phase += 1

        return self
        
    def resolve(self) -> SfgCallTreeNode:
        return SfgBranch(self._cond, self._branch_true, self._branch_false)
    
    