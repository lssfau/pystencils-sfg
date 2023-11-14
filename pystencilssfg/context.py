from typing import Generator, Union, Optional, Sequence
from dataclasses import dataclass

import sys
import os
from os import path

from argparse import ArgumentParser

from jinja2.filters import do_indent

from pystencils import Field
from pystencils.astnodes import KernelFunction

from .kernel_namespace import SfgKernelNamespace, SfgKernelHandle
from .tree import SfgCallTreeNode, SfgSequence, SfgKernelCallNode, SfgStatements
from .tree.deferred_nodes import SfgDeferredFieldMapping
from .tree.builders import SfgBranchBuilder, make_sequence
from .tree.visitors import CollectIncludes
from .source_concepts import SrcField, TypedSymbolOrObject
from .source_components import SfgFunction, SfgHeaderInclude


@dataclass
class SfgCodeStyle:
    indent_width: int = 2

    def indent(self, s: str):
        return do_indent(s, self.indent_width, first=True)


class SourceFileGenerator:
    def __init__(self,
                 namespace: str = "pystencils",
                 codestyle: SfgCodeStyle = SfgCodeStyle()):
        
        parser = ArgumentParser(
            "pystencilssfg",
            description="pystencils Source File Generator",
            allow_abbrev=False)
        
        parser.add_argument("-d", "--sfg-output-dir", type=str, default='.', dest='output_directory')

        generator_args, script_args = parser.parse_known_args(sys.argv)

        import __main__
        scriptpath = __main__.__file__
        scriptname = path.split(scriptpath)[1]
        basename = path.splitext(scriptname)[0]        

        self._context = SfgContext(script_args, namespace, codestyle)

        from .emitters.cpu.basic_cpu import BasicCpuEmitter
        self._emitter = BasicCpuEmitter(self._context, basename, generator_args.output_directory)

    def clean_files(self):
        for file in self._emitter.output_files:
            if path.exists(file):
                os.remove(file)

    def __enter__(self):
        self.clean_files()
        return self._context

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self._emitter.write_files()


class SfgContext:
    def __init__(self, argv, root_namespace: str, codestyle: SfgCodeStyle):
        self._argv = argv
        self._root_namespace = root_namespace
        self._codestyle = codestyle
        self._default_kernel_namespace = SfgKernelNamespace(self, "kernels")

        #   Source Components
        self._includes = set()
        self._kernel_namespaces = { self._default_kernel_namespace.name : self._default_kernel_namespace }
        self._functions = dict()

    @property
    def argv(self) -> Sequence[str]:
        return self._argv

    @property
    def root_namespace(self) -> str:
        return self._root_namespace
    
    @property
    def codestyle(self) -> SfgCodeStyle:
        return self._codestyle

    #----------------------------------------------------------------------------------------------
    #   Source Component Getters
    #----------------------------------------------------------------------------------------------
    
    def includes(self) -> Generator[SfgHeaderInclude, None, None]:
        yield from self._includes

    def kernel_namespaces(self) -> Generator[SfgKernelNamespace, None, None]:
        yield from self._kernel_namespaces.values()

    def functions(self) -> Generator[SfgFunction, None, None]:
        yield from self._functions.values()

    #----------------------------------------------------------------------------------------------
    #   Source Component Adders
    #----------------------------------------------------------------------------------------------

    def add_include(self, include: SfgHeaderInclude):
        self._includes.add(include)

    def add_function(self, func: SfgFunction):
        if func.name in self._functions:
            raise ValueError(f"Duplicate function: {func.name}")
        
        self._functions[func.name] = func
        for incl in CollectIncludes().visit(func._tree):
            self.add_include(incl)

    #----------------------------------------------------------------------------------------------
    #   Factory-like Adders
    #----------------------------------------------------------------------------------------------

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
                tree = make_sequence(*args)
                func = SfgFunction(self, name, tree)
                self.add_function(func)

            return sequencer
        

    #----------------------------------------------------------------------------------------------
    #   In-Sequence builders to be used within the second phase of SfgContext.function().
    #----------------------------------------------------------------------------------------------

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
    