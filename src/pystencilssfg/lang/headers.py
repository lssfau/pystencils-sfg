from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class HeaderFile:
    """Represents a C++ header file."""

    filepath: str
    """(Relative) path of this header file"""

    system_header: bool = False
    """Whether or not this is a system header."""

    def __str__(self) -> str:
        if self.system_header:
            return f"<{self.filepath}>"
        else:
            return self.filepath

    @staticmethod
    def parse(header: str | HeaderFile):
        if isinstance(header, HeaderFile):
            return header

        system_header = False
        if header.startswith('"') and header.endswith('"'):
            header = header[1:-1]

        if header.startswith("<") and header.endswith(">"):
            header = header[1:-1]
            system_header = True

        return HeaderFile(header, system_header=system_header)
