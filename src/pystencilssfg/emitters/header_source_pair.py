from typing import cast
from jinja2 import Environment, PackageLoader, StrictUndefined
from textwrap import indent

from os import path

from ..context import SfgContext


class HeaderSourcePairEmitter:
    def __init__(self,
                 basename: str,
                 header_extension: str,
                 impl_extension: str,
                 output_directory: str):
        self._basename = basename
        self._output_directory = cast(str, output_directory)
        self._header_filename = f"{basename}.{header_extension}"
        self._source_filename = f"{basename}.{impl_extension}"

    @property
    def output_files(self) -> tuple[str, str]:
        return (
            path.join(self._output_directory, self._header_filename),
            path.join(self._output_directory, self._source_filename)
        )

    def write_files(self, ctx: SfgContext):
        fq_namespace = ctx.fully_qualified_namespace

        jinja_context = {
            'ctx': ctx,
            'header_filename': self._header_filename,
            'source_filename': self._source_filename,
            'basename': self._basename,
            'prelude': get_prelude_comment(ctx),
            'definitions': list(ctx.definitions()),
            'fq_namespace': fq_namespace,
            'public_includes': list(incl.get_code() for incl in ctx.includes() if not incl.private),
            'private_includes': list(incl.get_code() for incl in ctx.includes() if incl.private),
            'kernel_namespaces': list(ctx.kernel_namespaces()),
            'functions': list(ctx.functions())
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

        with open(path.join(self._output_directory, self._header_filename), 'w') as headerfile:
            headerfile.write(header)

        with open(path.join(self._output_directory, self._source_filename), 'w') as cppfile:
            cppfile.write(source)


def get_prelude_comment(ctx: SfgContext):
    if not ctx.prelude_comment:
        return ""

    return "/*\n" + indent(ctx.prelude_comment, "* ", predicate=lambda _: True) + "*/\n"
