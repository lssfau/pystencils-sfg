from jinja2 import Environment, PackageLoader, StrictUndefined

from os import path, makedirs

from ..configuration import SfgOutputSpec
from ..context import SfgContext

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
            path.join(self._output_directory, self._impl_filename)
        )

    def write_files(self, ctx: SfgContext):
        fq_namespace = ctx.fully_qualified_namespace

        jinja_context = {
            'ctx': ctx,
            'header_filename': self._header_filename,
            'source_filename': self._impl_filename,
            'basename': self._basename,
            'prelude_comment': ctx.prelude_comment,
            'definitions': tuple(ctx.definitions()),
            'fq_namespace': fq_namespace,
            'public_includes': tuple(incl.get_code() for incl in ctx.includes() if not incl.private),
            'private_includes': tuple(incl.get_code() for incl in ctx.includes() if incl.private),
            'kernel_namespaces': tuple(ctx.kernel_namespaces()),
            'functions': tuple(ctx.functions()),
            'classes': tuple(ctx.classes())
        }

        template_name = "HeaderSourcePair"

        env = Environment(loader=PackageLoader('pystencilssfg.emitters'),
                          undefined=StrictUndefined,
                          trim_blocks=True,
                          lstrip_blocks=True)

        from .jinja_filters import add_filters_to_jinja
        add_filters_to_jinja(env)

        header = env.get_template(f"{template_name}.tmpl.h").render(**jinja_context)
        source = env.get_template(f"{template_name}.tmpl.cpp").render(**jinja_context)

        header = invoke_clang_format(header, ctx.codestyle)
        source = invoke_clang_format(source, ctx.codestyle)

        makedirs(self._output_directory, exist_ok=True)

        with open(self._ospec.get_header_filepath(), 'w') as headerfile:
            headerfile.write(header)

        with open(self._ospec.get_impl_filepath(), 'w') as cppfile:
            cppfile.write(source)
