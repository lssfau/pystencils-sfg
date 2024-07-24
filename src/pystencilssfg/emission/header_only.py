from typing import Sequence
from os import path, makedirs

from ..configuration import SfgOutputSpec
from ..context import SfgContext
from .prepare import prepare_context
from .printers import SfgHeaderPrinter
from .clang_format import invoke_clang_format

from .emitter import AbstractEmitter


class HeaderOnlyEmitter(AbstractEmitter):
    def __init__(self, output_spec: SfgOutputSpec):
        """Create a `HeaderImplPairEmitter` from an [SfgOutputSpec][pystencilssfg.configuration.SfgOutputSpec]."""
        self._basename = output_spec.basename
        self._output_directory = output_spec.output_directory
        self._header_filename = output_spec.get_header_filename()

        self._ospec = output_spec

    @property
    def output_files(self) -> Sequence[str]:
        """The files that will be written by `write_files`."""
        return (path.join(self._output_directory, self._header_filename),)

    def write_files(self, ctx: SfgContext):
        ctx = prepare_context(ctx)

        header_printer = SfgHeaderPrinter(ctx, self._ospec)
        header = header_printer.get_code()
        header = invoke_clang_format(header, ctx.codestyle)

        makedirs(self._output_directory, exist_ok=True)

        with open(self._ospec.get_header_filepath(), "w") as headerfile:
            headerfile.write(header)
