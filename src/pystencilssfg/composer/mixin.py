from __future__ import annotations

from ..context import SfgContext, SfgCursor
from .basic_composer import SfgBasicComposer


class SfgComposerMixIn:
    #   type: ignore
    def __new__(cls, *args, **kwargs):
        if not issubclass(cls, SfgBasicComposer):
            raise Exception(f"{cls} must be mixed-in with SfgBasicComposer.")
        else:
            return super().__new__(cls)

    def __init__(self) -> None:
        self._ctx: SfgContext
        self._cursor: SfgCursor

    @property
    def _composer(self) -> SfgBasicComposer:
        assert isinstance(self, SfgBasicComposer)
        return self
