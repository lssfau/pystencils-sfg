from typing import Sequence
from os import path, makedirs

from ..context import SfgContext
from .prepare import prepare_context
from .printers import SfgHeaderPrinter
from ..config import ClangFormatOptions
from .clang_format import invoke_clang_format

from .emitter import AbstractEmitter, OutputSpec


class HeaderOnlyEmitter(AbstractEmitter):
    def __init__(
        self, output_spec: OutputSpec, clang_format: ClangFormatOptions | None = None
    ):
        """Create a `HeaderImplPairEmitter` from an [SfgOutputSpec][pystencilssfg.configuration.SfgOutputSpec]."""
        self._basename = output_spec.basename
        self._output_directory = output_spec.output_directory
        self._header_filename = output_spec.get_header_filename()

        self._ospec = output_spec
        self._clang_format = clang_format

    @property
    def output_files(self) -> Sequence[str]:
        """The files that will be written by `write_files`."""
        return (path.join(self._output_directory, self._header_filename),)

    def write_files(self, ctx: SfgContext):
        ctx = prepare_context(ctx)

        header_printer = SfgHeaderPrinter(ctx, self._ospec)
        header = header_printer.get_code()
        if self._clang_format is not None:
            header = invoke_clang_format(header, self._clang_format)

        makedirs(self._output_directory, exist_ok=True)

        with open(self._ospec.get_header_filepath(), "w") as headerfile:
            headerfile.write(header)
