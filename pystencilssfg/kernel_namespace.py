from typing import Sequence

from pystencils import CreateKernelConfig, create_kernel
from pystencils.astnodes import KernelFunction

class SfgKernelNamespace:
    def __init__(self, ctx, name: str):
        self._ctx = ctx
        self._name = name
        self._asts = dict()

    @property
    def name(self):
        return self._name

    @property
    def asts(self):
        yield from self._asts.values()

    def add(self, ast: KernelFunction):
        """Adds an existing pystencils AST to this namespace."""
        astname = ast.function_name
        if astname in self._asts:
            raise ValueError(f"Duplicate ASTs: An AST with name {astname} already exists in namespace {self._name}")

        self._asts[astname] = ast

        return SfgKernelHandle(self._ctx, astname, self, ast.get_parameters())

    def create(self, assignments, config: CreateKernelConfig = None):
        ast = create_kernel(assignments, config=config)
        return self.add(ast)


class SfgKernelHandle:
    def __init__(self, ctx, name: str, namespace: SfgKernelNamespace, parameters: Sequence[KernelFunction.Parameter]):
        self._ctx = ctx
        self._name = name
        self._namespace = namespace
        self._parameters = parameters

        self._scalar_params = set()
        self._fields = set()

        for param in self._parameters:
            if param.is_field_parameter:
                self._fields |= set(param.fields)
            else:
                self._scalar_params.add(param.symbol)

    @property
    def kernel_name(self):
        return self._name

    @property
    def kernel_namespace(self):
        return self._namespace

    @property
    def fully_qualified_name(self):
        return f"{self._ctx.root_namespace}::{self.kernel_namespace.name}::{self.kernel_name}"
    
    @property
    def parameters(self):
        return self._parameters

    @property
    def scalar_parameters(self):
        return self._scalar_params

    @property
    def fields(self):
        return self.fields
    