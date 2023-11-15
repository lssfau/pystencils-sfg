from typing import Generator, Union, Optional, Sequence

import sys
import os
from os import path


from pystencils import Field
from pystencils.astnodes import KernelFunction

from .configuration import SfgConfiguration, config_from_commandline, merge_configurations, SfgCodeStyle
from .kernel_namespace import SfgKernelNamespace, SfgKernelHandle
from .tree import SfgCallTreeNode, SfgSequence, SfgKernelCallNode, SfgStatements
from .tree.deferred_nodes import SfgDeferredFieldMapping
from .tree.builders import SfgBranchBuilder, make_sequence
from .tree.visitors import CollectIncludes
from .source_concepts import SrcField, TypedSymbolOrObject
from .source_components import SfgFunction, SfgHeaderInclude


class SourceFileGenerator:
    def __init__(self, sfg_config: SfgConfiguration = None):
        if sfg_config and not isinstance(sfg_config, SfgConfiguration):
            raise TypeError("sfg_config is not an SfgConfiguration.")

        import __main__
        scriptpath = __main__.__file__
        scriptname = path.split(scriptpath)[1]
        basename = path.splitext(scriptname)[0]

        project_config, cmdline_config, script_args = config_from_commandline(sys.argv)

        config = merge_configurations(project_config, cmdline_config, sfg_config)

        self._context = SfgContext(script_args, config)

        from .emitters.cpu.basic_cpu import BasicCpuEmitter
        self._emitter = BasicCpuEmitter(basename, config)

    def clean_files(self):
        for file in self._emitter.output_files:
            if path.exists(file):
                os.remove(file)

    def __enter__(self):
        self.clean_files()
        return self._context

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self._emitter.write_files(self._context)


class SfgContext:
    def __init__(self, argv, config: SfgConfiguration):
        self._argv = argv
        self._config = config
        self._default_kernel_namespace = SfgKernelNamespace(self, "kernels")

        self._code_namespace = None

        #   Source Components
        self._includes = set()
        self._kernel_namespaces = {self._default_kernel_namespace.name: self._default_kernel_namespace}
        self._functions = dict()

    @property
    def argv(self) -> Sequence[str]:
        return self._argv

    @property
    def root_namespace(self) -> str:
        return self._config.base_namespace

    @property
    def inner_namespace(self) -> str:
        return self._code_namespace

    @property
    def fully_qualified_namespace(self) -> str:
        match (self.root_namespace, self.inner_namespace):
            case None, None: return None
            case outer, None: return outer
            case None, inner: return inner
            case outer, inner: return f"{outer}::{inner}"

    @property
    def codestyle(self) -> SfgCodeStyle:
        return self._config.codestyle

    # ----------------------------------------------------------------------------------------------
    #   Source Component Getters
    # ----------------------------------------------------------------------------------------------

    def includes(self) -> Generator[SfgHeaderInclude, None, None]:
        yield from self._includes

    def kernel_namespaces(self) -> Generator[SfgKernelNamespace, None, None]:
        yield from self._kernel_namespaces.values()

    def functions(self) -> Generator[SfgFunction, None, None]:
        yield from self._functions.values()

    # ----------------------------------------------------------------------------------------------
    #   Source Component Adders
    # ----------------------------------------------------------------------------------------------

    def add_include(self, include: SfgHeaderInclude):
        self._includes.add(include)

    def add_function(self, func: SfgFunction):
        if func.name in self._functions:
            raise ValueError(f"Duplicate function: {func.name}")

        self._functions[func.name] = func
        for incl in CollectIncludes().visit(func._tree):
            self.add_include(incl)

    # ----------------------------------------------------------------------------------------------
    #   Factory-like Adders
    # ----------------------------------------------------------------------------------------------

    @property
    def kernels(self) -> SfgKernelNamespace:
        return self._default_kernel_namespace

    def kernel_namespace(self, name: str) -> SfgKernelNamespace:
        if name in self._kernel_namespaces:
            raise ValueError(f"Duplicate kernel namespace: {name}")

        kns = SfgKernelNamespace(self, name)
        self._kernel_namespaces[name] = kns
        return kns

    def include(self, header_file: str):
        system_header = False
        if header_file.startswith("<") and header_file.endswith(">"):
            header_file = header_file[1:-1]
            system_header = True

        self.add_include(SfgHeaderInclude(header_file, system_header=system_header))

    def function(self,
                 name: str,
                 ast_or_kernel_handle: Optional[Union[KernelFunction, SfgKernelHandle]] = None):
        if name in self._functions:
            raise ValueError(f"Duplicate function: {name}")

        if ast_or_kernel_handle is not None:
            if isinstance(ast_or_kernel_handle, KernelFunction):
                khandle = self._default_kernel_namespace.add(ast_or_kernel_handle)
                tree = SfgKernelCallNode(khandle)
            elif isinstance(ast_or_kernel_handle, SfgKernelCallNode):
                tree = ast_or_kernel_handle
            else:
                raise TypeError("Invalid type of argument `ast_or_kernel_handle`!")

            func = SfgFunction(self, name, tree)
            self.add_function(func)
        else:
            def sequencer(*args: SfgCallTreeNode):
                tree = make_sequence(*args)
                func = SfgFunction(self, name, tree)
                self.add_function(func)

            return sequencer

    # ----------------------------------------------------------------------------------------------
    #   In-Sequence builders to be used within the second phase of SfgContext.function().
    # ----------------------------------------------------------------------------------------------

    def call(self, kernel_handle: SfgKernelHandle) -> SfgKernelCallNode:
        return SfgKernelCallNode(kernel_handle)

    @property
    def branch(self) -> SfgBranchBuilder:
        return SfgBranchBuilder()

    def map_field(self, field: Field, src_object: Optional[SrcField] = None) -> SfgSequence:
        if src_object is None:
            raise NotImplementedError("Automatic field extraction is not implemented yet.")
        else:
            return SfgDeferredFieldMapping(field, src_object)

    def map_param(self, lhs: TypedSymbolOrObject, rhs: TypedSymbolOrObject, mapping: str):
        return SfgStatements(mapping, (lhs,), (rhs,))
