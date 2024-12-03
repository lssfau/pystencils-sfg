from __future__ import annotations

from typing import Sequence
from abc import ABC, abstractmethod
from dataclasses import dataclass
from os import path

from ..context import SfgContext
from ..config import SfgConfig, OutputMode


@dataclass
class OutputSpec:
    """Name and path specification for files output by the code generator.

    Filenames are constructed as `<output_directory>/<basename>.<extension>`."""

    output_directory: str
    """Directory to which the generated files should be written."""

    basename: str
    """Base name for output files."""

    header_extension: str
    """File extension for generated header file."""

    impl_extension: str
    """File extension for generated implementation file."""

    def get_header_filename(self):
        return f"{self.basename}.{self.header_extension}"

    def get_impl_filename(self):
        return f"{self.basename}.{self.impl_extension}"

    def get_header_filepath(self):
        return path.join(self.output_directory, self.get_header_filename())

    def get_impl_filepath(self):
        return path.join(self.output_directory, self.get_impl_filename())

    @staticmethod
    def create(config: SfgConfig, basename: str) -> OutputSpec:
        output_mode = config.get_option("output_mode")
        header_extension = config.extensions.get_option("header")
        impl_extension = config.extensions.get_option("impl")

        if impl_extension is None:
            match output_mode:
                case OutputMode.INLINE:
                    impl_extension = "ipp"
                case OutputMode.STANDALONE:
                    impl_extension = "cpp"

        return OutputSpec(
            config.get_option("output_directory"),
            basename,
            header_extension,
            impl_extension,
        )


class AbstractEmitter(ABC):
    @property
    @abstractmethod
    def output_files(self) -> Sequence[str]:
        pass

    @abstractmethod
    def write_files(self, ctx: SfgContext):
        pass
