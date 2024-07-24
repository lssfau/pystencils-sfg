from typing import Sequence
from abc import ABC, abstractmethod

from ..context import SfgContext


class AbstractEmitter(ABC):
    @property
    @abstractmethod
    def output_files(self) -> Sequence[str]:
        pass

    @abstractmethod
    def write_files(self, ctx: SfgContext):
        pass
