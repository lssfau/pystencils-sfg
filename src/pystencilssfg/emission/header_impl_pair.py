from typing import Sequence
from os import path, makedirs

from ..context import SfgContext
from .printers import SfgHeaderPrinter, SfgImplPrinter
from .clang_format import invoke_clang_format
from ..config import ClangFormatOptions

from .emitter import AbstractEmitter, OutputSpec


class HeaderImplPairEmitter(AbstractEmitter):
    """Emits a header-implementation file pair."""

    def __init__(
        self,
        output_spec: OutputSpec,
        inline_impl: bool = False,
        clang_format: ClangFormatOptions | None = None,
    ):
        """Create a `HeaderImplPairEmitter` from an [SfgOutputSpec][pystencilssfg.configuration.SfgOutputSpec]."""
        self._basename = output_spec.basename
        self._output_directory = output_spec.output_directory
        self._header_filename = output_spec.get_header_filename()
        self._impl_filename = output_spec.get_impl_filename()
        self._inline_impl = inline_impl

        self._ospec = output_spec
        self._clang_format = clang_format

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
        header_printer = SfgHeaderPrinter(ctx, self._ospec, self._inline_impl)
        impl_printer = SfgImplPrinter(ctx, self._ospec, self._inline_impl)

        header = header_printer.get_code()
        impl = impl_printer.get_code()

        if self._clang_format is not None:
            header = invoke_clang_format(header, self._clang_format)
            impl = invoke_clang_format(impl, self._clang_format)

        makedirs(self._output_directory, exist_ok=True)

        with open(self._ospec.get_header_filepath(), "w") as headerfile:
            headerfile.write(header)

        with open(self._ospec.get_impl_filepath(), "w") as cppfile:
            cppfile.write(impl)
