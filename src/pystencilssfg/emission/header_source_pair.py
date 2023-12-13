from os import path, makedirs

from ..configuration import SfgOutputSpec
from ..context import SfgContext
from .prepare import prepare_context
from .printers import SfgHeaderPrinter, SfgImplPrinter

from .clang_format import invoke_clang_format


class HeaderSourcePairEmitter:
    def __init__(self, output_spec: SfgOutputSpec):
        self._basename = output_spec.basename
        self._output_directory = output_spec.output_directory
        self._header_filename = output_spec.get_header_filename()
        self._impl_filename = output_spec.get_impl_filename()

        self._ospec = output_spec

    @property
    def output_files(self) -> tuple[str, str]:
        return (
            path.join(self._output_directory, self._header_filename),
            path.join(self._output_directory, self._impl_filename),
        )

    def write_files(self, ctx: SfgContext):
        ctx = prepare_context(ctx)

        header_printer = SfgHeaderPrinter(ctx, self._ospec)
        impl_printer = SfgImplPrinter(ctx, self._ospec)

        header = header_printer.get_code()
        impl = impl_printer.get_code()

        header = invoke_clang_format(header, ctx.codestyle)
        impl = invoke_clang_format(impl, ctx.codestyle)

        makedirs(self._output_directory, exist_ok=True)

        with open(self._ospec.get_header_filepath(), "w") as headerfile:
            headerfile.write(header)

        with open(self._ospec.get_impl_filepath(), "w") as cppfile:
            cppfile.write(impl)
