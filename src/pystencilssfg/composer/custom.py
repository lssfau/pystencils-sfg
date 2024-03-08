from abc import ABC, abstractmethod
from ..context import SfgContext


class CustomGenerator(ABC):
    """Abstract base class for custom code generators that may be passed to
    [SfgComposer.generate][pystencilssfg.SfgComposer.generate]."""

    @abstractmethod
    def generate(self, ctx: SfgContext) -> None: ...
