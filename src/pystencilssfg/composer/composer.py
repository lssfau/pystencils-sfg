from __future__ import annotations
from typing import TYPE_CHECKING

from .basic_composer import SfgBasicComposer
from .class_composer import SfgClassComposer

if TYPE_CHECKING:
    from ..context import SfgContext


class SfgComposer(SfgBasicComposer, SfgClassComposer):
    """Primary interface for constructing source files in pystencils-sfg.

    The SfgComposer combines the `SfgBasicComposer`
    for the basic components (kernel namespaces, includes, definitions, and functions)
    and the `SfgClassComposer` for constructing ``struct`` s and ``class`` es.
    """

    def __init__(self, sfg: SfgContext | SfgBasicComposer):
        SfgBasicComposer.__init__(self, sfg)
        SfgClassComposer.__init__(self)
