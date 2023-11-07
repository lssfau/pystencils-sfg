from os import path

from .kernel_namespace import SfgKernelNamespace

class SourceFileGenerator:
    def __init__(self, namespace: str = "pystencils", basename: str = None):
        
        if basename is None:
            import __main__
            scriptpath = __main__.__file__
            scriptname = path.split(scriptpath)[1]
            basename = path.splitext(scriptname)[0]

        self.basename = basename
        self.header_filename = basename + ".h"
        self.cpp_filename = basename + ".cpp"

        self._context = SfgContext(namespace)

    def __enter__(self):
        return self._context

    def __exit__(self, *args):
        from .emitters.cpu.basic_cpu import BasicCpuEmitter
        BasicCpuEmitter(self._context, self.basename).write_files()


class SfgContext:
    def __init__(self, root_namespace: str):
        self._root_namespace = root_namespace
        self._default_kernel_namespace = SfgKernelNamespace(self, "kernels")

        self._kernel_namespaces = { self._default_kernel_namespace.name : self._default_kernel_namespace }

    @property
    def root_namespace(self):
        return self._root_namespace

    @property
    def kernels(self):
        return self._default_kernel_namespace

    def kernel_namespace(self, name):
        if name in self._kernel_namespaces:
            raise ValueError(f"Duplicate kernel namespace: {name}")

        kns = SfgKernelNamespace(self, name)
        self._kernel_namespaces[name] = kns
        return kns

    @property
    def kernel_namespaces(self):
        yield from self._kernel_namespaces.values()
