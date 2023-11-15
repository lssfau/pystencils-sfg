from jinja2 import Environment, PackageLoader, StrictUndefined

from os import path

from ...configuration import SfgConfiguration
from ...context import SfgContext

class BasicCpuEmitter:
    def __init__(self, basename: str, config: SfgConfiguration):
        self._basename = basename
        self._output_directory = config.output_directory
        self._header_filename = f"{basename}.{config.header_extension}"
        self._cpp_filename = f"{basename}.{config.source_extension}"

    @property
    def output_files(self) -> str:
        return (
            path.join(self._output_directory, self._header_filename),
            path.join(self._output_directory, self._cpp_filename)
        )

    def write_files(self, ctx: SfgContext):
        jinja_context = {
            'ctx': ctx,
            'basename': self._basename,
            'root_namespace': ctx.root_namespace,
            'public_includes': list(incl.get_code() for incl in ctx.includes() if not incl.private),
            'private_includes': list(incl.get_code() for incl in ctx.includes() if incl.private),
            'kernel_namespaces': list(ctx.kernel_namespaces()),
            'functions': list(ctx.functions())
        }

        template_name = "BasicCpu"

        env = Environment(loader=PackageLoader('pystencilssfg.emitters.cpu'), undefined=StrictUndefined)

        from .jinja_filters import add_filters_to_jinja
        add_filters_to_jinja(env)

        header = env.get_template(f"{template_name}.tmpl.h").render(**jinja_context)
        source = env.get_template(f"{template_name}.tmpl.cpp").render(**jinja_context)

        with open(path.join(self._output_directory, self._header_filename), 'w') as headerfile:
            headerfile.write(header)

        with open(path.join(self._output_directory, self._cpp_filename), 'w') as cppfile:
            cppfile.write(source)
