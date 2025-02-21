from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .composer import SfgComposer


class CustomGenerator(ABC):
    """Abstract base class for custom code generators that may be passed to
    `SfgBasicComposer.generate`."""

    @abstractmethod
    def generate(self, sfg: SfgComposer) -> None: ...
