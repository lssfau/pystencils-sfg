from jinja2 import Environment, PackageLoader, StrictUndefined

from os import path

from ...context import SfgContext

class BasicCpuEmitter:
    def __init__(self, ctx: SfgContext, basename: str, output_directory: str):
        self._ctx = ctx
        self._basename = basename
        self._output_directory = output_directory
        self._header_filename = basename + ".h"
        self._cpp_filename = basename + ".cpp"

    @property
    def output_files(self) -> str:
        return (
            path.join(self._output_directory, self._header_filename),
            path.join(self._output_directory, self._cpp_filename)
        )

    def write_files(self):
        jinja_context = {
            'ctx': self._ctx,
            'basename': self._basename,
            'root_namespace': self._ctx.root_namespace,
            'public_includes': list(incl.get_code() for incl in self._ctx.includes() if not incl.private),
            'private_includes': list(incl.get_code() for incl in self._ctx.includes() if incl.private),
            'kernel_namespaces': list(self._ctx.kernel_namespaces()),
            'functions': list(self._ctx.functions())
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
