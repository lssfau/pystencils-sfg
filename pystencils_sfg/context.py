from typing import Callable, Sequence, Generator, Union, Optional
from dataclasses import dataclass

import os
from os import path

from jinja2.filters import do_indent

from pystencils.astnodes import KernelFunction

from .kernel_namespace import SfgKernelNamespace, SfgKernelHandle
from .tree import SfgCallTreeNode, SfgSequence, SfgKernelCallNode, SfgCondition, SfgBranch
from .tree.builders import SfgBranchBuilder, SfgSequencer
from .source_components import SfgFunction


@dataclass
class SfgCodeStyle:
    indent_width: int = 2

    def indent(self, s: str):
        return do_indent(s, self.indent_width, first=True)


class SourceFileGenerator:
    def __init__(self,
                 namespace: str = "pystencils",
                 basename: str = None,
                 codestyle: SfgCodeStyle = SfgCodeStyle()):
        
        if basename is None:
            import __main__
            scriptpath = __main__.__file__
            scriptname = path.split(scriptpath)[1]
            basename = path.splitext(scriptname)[0]

        self.basename = basename
        self.header_filename = basename + ".h"
        self.cpp_filename = basename + ".cpp"

        self._context = SfgContext(namespace, codestyle)

    def clean_files(self):
        for file in (self.header_filename, self.cpp_filename):
            if path.exists(file):
                os.remove(file)

    def __enter__(self):
        self.clean_files()
        return self._context

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            from .emitters.cpu.basic_cpu import BasicCpuEmitter
            BasicCpuEmitter(self._context, self.basename).write_files()


class SfgContext:
    def __init__(self, root_namespace: str, codestyle: SfgCodeStyle):
        self._root_namespace = root_namespace
        self._codestyle = codestyle
        self._default_kernel_namespace = SfgKernelNamespace(self, "kernels")

        #   Source Components
        self._includes = []
        self._kernel_namespaces = { self._default_kernel_namespace.name : self._default_kernel_namespace }
        self._functions = dict()

        #   Builder Components
        self._sequencer = SfgSequencer(self)

    @property
    def root_namespace(self) -> str:
        return self._root_namespace
    
    @property
    def codestyle(self) -> SfgCodeStyle:
        return self._codestyle

    @property
    def kernels(self) -> SfgKernelNamespace:
        return self._default_kernel_namespace

    def kernel_namespace(self, name: str) -> SfgKernelNamespace:
        if name in self._kernel_namespaces:
            raise ValueError(f"Duplicate kernel namespace: {name}")

        kns = SfgKernelNamespace(self, name)
        self._kernel_namespaces[name] = kns
        return kns

    def kernel_namespaces(self) -> Generator[SfgKernelNamespace, None, None]:
        yield from self._kernel_namespaces.values()

    def functions(self) -> Generator[SfgFunction, None, None]:
        yield from self._functions.values()

    def include(self, header_file: str):
        self._includes.append(header_file)

    def function(self, 
                 name: str,
                 ast_or_kernel_handle : Optional[Union[KernelFunction, SfgKernelHandle]] = None):
        if name in self._functions:
            raise ValueError(f"Duplicate function: {name}")
        
        if ast_or_kernel_handle is not None:
            if isinstance(ast_or_kernel_handle, KernelFunction):
                khandle = self._default_kernel_namespace.add(ast_or_kernel_handle)
                tree = SfgKernelCallNode(self, khandle)
            elif isinstance(ast_or_kernel_handle, SfgKernelCallNode):
                tree = ast_or_kernel_handle
            else:
                raise TypeError(f"Invalid type of argument `ast_or_kernel_handle`!")
        else:
            def sequencer(*args: SfgCallTreeNode):
                tree = self.seq(*args)
                func = SfgFunction(self, name, tree)
                self._functions[name] = func

            return sequencer
        

    #----------------------------------------------------------------------------------------------
    #   Call Tree Node Factory
    #----------------------------------------------------------------------------------------------

    @property
    def seq(self) -> SfgSequencer:
        return self._sequencer

    def call(self, kernel_handle: SfgKernelHandle) -> SfgKernelCallNode:
        return SfgKernelCallNode(kernel_handle)
    
    @property
    def branch(self) -> SfgBranchBuilder:
        return SfgBranchBuilder(self)
    