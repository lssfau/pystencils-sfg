from jinja2 import Environment, PackageLoader, StrictUndefined

from ...context import SfgContext

class BasicCpuEmitter:
    def __init__(self, ctx: SfgContext, basename: str):
        self._ctx = ctx
        self._basename = basename
        self._header_filename = basename + ".h"
        self._cpp_filename = basename + ".cpp"

    def write_files(self):
        jinja_context = {
            'ctx': self._ctx,
            'basename': self._basename,
            'root_namespace': self._ctx.root_namespace,
            'kernel_namespaces': list(self._ctx.kernel_namespaces)
        }

        template_name = "BasicCpu"

        env = Environment(loader=PackageLoader('pystencils_sfg.emitters.cpu'), undefined=StrictUndefined)

        from .jinja_filters import add_filters_to_jinja
        add_filters_to_jinja(env)

        header = env.get_template(f"{template_name}.tmpl.h").render(**jinja_context)
        source = env.get_template(f"{template_name}.tmpl.cpp").render(**jinja_context)

        with open(self._header_filename, 'w') as headerfile:
            headerfile.write(header)

        with open(self._cpp_filename, 'w') as cppfile:
            cppfile.write(source)
