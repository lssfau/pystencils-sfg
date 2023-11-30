from typing import Generator, Sequence

from .configuration import SfgConfiguration, SfgCodeStyle
from .tree.visitors import CollectIncludes
from .source_components import SfgHeaderInclude, SfgKernelNamespace, SfgFunction
from .exceptions import SfgException


class SfgContext:
    def __init__(self, config: SfgConfiguration, argv: Sequence[str] | None = None):
        self._argv = argv
        self._config = config
        self._default_kernel_namespace = SfgKernelNamespace(self, "kernels")

        self._code_namespace = None

        #   Source Components
        self._includes: set[SfgHeaderInclude] = set()
        self._kernel_namespaces = {self._default_kernel_namespace.name: self._default_kernel_namespace}
        self._functions: dict[str, SfgFunction] = dict()

    @property
    def argv(self) -> Sequence[str]:
        """If this context was created by a `pystencilssfg.SourceFileGenerator`, provides the command
        line arguments given to the generator script, with configuration arguments for the code generator
        stripped away.

        Otherwise, throws an exception."""
        if self._argv is None:
            raise SfgException("This context provides no command-line arguments.")
        return self._argv

    @property
    def root_namespace(self) -> str | None:
        return self._config.base_namespace

    @property
    def inner_namespace(self) -> str | None:
        return self._code_namespace

    @property
    def fully_qualified_namespace(self) -> str | None:
        match (self.root_namespace, self.inner_namespace):
            case None, None: return None
            case outer, None: return outer
            case None, inner: return inner
            case outer, inner: return f"{outer}::{inner}"
            case _: assert False

    @property
    def codestyle(self) -> SfgCodeStyle:
        assert self._config.codestyle is not None
        return self._config.codestyle

    # ----------------------------------------------------------------------------------------------
    #   Kernel Namespaces
    # ----------------------------------------------------------------------------------------------

    def includes(self) -> Generator[SfgHeaderInclude, None, None]:
        yield from self._includes

    def add_include(self, include: SfgHeaderInclude):
        self._includes.add(include)

    # ----------------------------------------------------------------------------------------------
    #   Kernel Namespaces
    # ----------------------------------------------------------------------------------------------

    @property
    def default_kernel_namespace(self) -> SfgKernelNamespace:
        return self._default_kernel_namespace

    def kernel_namespaces(self) -> Generator[SfgKernelNamespace, None, None]:
        yield from self._kernel_namespaces.values()

    def get_kernel_namespace(self, str) -> SfgKernelNamespace | None:
        return self._kernel_namespaces.get(str)

    def add_kernel_namespace(self, namespace: SfgKernelNamespace):
        if namespace.name in self._kernel_namespaces:
            raise ValueError(f"Duplicate kernel namespace: {namespace.name}")

        self._kernel_namespaces[namespace.name] = namespace

    # ----------------------------------------------------------------------------------------------
    #   Functions
    # ----------------------------------------------------------------------------------------------

    def functions(self) -> Generator[SfgFunction, None, None]:
        yield from self._functions.values()

    def get_function(self, name: str) -> SfgFunction | None:
        return self._functions.get(name, None)

    def add_function(self, func: SfgFunction) -> None:
        if func.name in self._functions:
            raise ValueError(f"Duplicate function: {func.name}")

        self._functions[func.name] = func
        for incl in CollectIncludes().visit(func._tree):
            self.add_include(incl)
