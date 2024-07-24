from typing import Sequence
from os import path, makedirs

from ..configuration import SfgOutputSpec
from ..context import SfgContext
from .prepare import prepare_context
from .printers import SfgHeaderPrinter, SfgImplPrinter
from .clang_format import invoke_clang_format

from .emitter import AbstractEmitter


class HeaderImplPairEmitter(AbstractEmitter):
    """Emits a header-implementation file pair."""

    def __init__(self, output_spec: SfgOutputSpec, inline_impl: bool = False):
        """Create a `HeaderImplPairEmitter` from an [SfgOutputSpec][pystencilssfg.configuration.SfgOutputSpec]."""
        self._basename = output_spec.basename
        self._output_directory = output_spec.output_directory
        self._header_filename = output_spec.get_header_filename()
        self._impl_filename = output_spec.get_impl_filename()
        self._inline_impl = inline_impl

        self._ospec = output_spec

    @property
    def output_files(self) -> Sequence[str]:
        """The files that will be written by `write_files`."""
        return (
            path.join(self._output_directory, self._header_filename),
            path.join(self._output_directory, self._impl_filename),
        )

    def write_files(self, ctx: SfgContext):
        """Write the code represented by the given [SfgContext][pystencilssfg.SfgContext] to the files
        specified by the output specification."""
        ctx = prepare_context(ctx)

        header_printer = SfgHeaderPrinter(ctx, self._ospec, self._inline_impl)
        impl_printer = SfgImplPrinter(ctx, self._ospec, self._inline_impl)

        header = header_printer.get_code()
        impl = impl_printer.get_code()

        header = invoke_clang_format(header, ctx.codestyle)
        impl = invoke_clang_format(impl, ctx.codestyle)

        makedirs(self._output_directory, exist_ok=True)

        with open(self._ospec.get_header_filepath(), "w") as headerfile:
            headerfile.write(header)

        with open(self._ospec.get_impl_filepath(), "w") as cppfile:
            cppfile.write(impl)
