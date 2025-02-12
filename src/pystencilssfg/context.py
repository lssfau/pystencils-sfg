from __future__ import annotations
from typing import Sequence, Any, Generator
from contextlib import contextmanager

from .config import CodeStyle
from .ir import (
    SfgSourceFile,
    SfgNamespace,
    SfgNamespaceBlock,
    SfgCodeEntity,
    SfgGlobalNamespace,
)
from .ir.syntax import SfgNamespaceElement
from .exceptions import SfgException


class SfgContext:
    """Manages context information during the execution of a generator script."""

    def __init__(
        self,
        header_file: SfgSourceFile,
        impl_file: SfgSourceFile | None,
        namespace: str | None = None,
        codestyle: CodeStyle | None = None,
        argv: Sequence[str] | None = None,
        project_info: Any = None,
    ):
        self._argv = argv
        self._project_info = project_info

        self._outer_namespace = namespace
        self._inner_namespace: str | None = None

        self._codestyle = codestyle if codestyle is not None else CodeStyle()

        self._header_file = header_file
        self._impl_file = impl_file

        self._global_namespace = SfgGlobalNamespace()

        current_namespace: SfgNamespace
        if namespace is not None:
            current_namespace = self._global_namespace.get_child_namespace(namespace)
        else:
            current_namespace = self._global_namespace

        self._cursor = SfgCursor(self, current_namespace)

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
    def project_info(self) -> Any:
        """Project-specific information provided by a build system."""
        return self._project_info

    @property
    def outer_namespace(self) -> str | None:
        """Outer code namespace. Set by constructor argument `outer_namespace`."""
        return self._outer_namespace

    @property
    def codestyle(self) -> CodeStyle:
        """The code style object for this generation context."""
        return self._codestyle

    @property
    def header_file(self) -> SfgSourceFile:
        return self._header_file

    @property
    def impl_file(self) -> SfgSourceFile | None:
        return self._impl_file

    @property
    def cursor(self) -> SfgCursor:
        return self._cursor

    @property
    def files(self) -> Generator[SfgSourceFile, None, None]:
        yield self._header_file
        if self._impl_file is not None:
            yield self._impl_file

    @property
    def global_namespace(self) -> SfgNamespace:
        return self._global_namespace


class SfgCursor:
    """Cursor that tracks the current location in the source file(s) during execution of the generator script."""

    def __init__(self, ctx: SfgContext, namespace: SfgNamespace) -> None:
        self._ctx = ctx

        self._cur_namespace: SfgNamespace = namespace

        self._loc: dict[SfgSourceFile, list[SfgNamespaceElement]] = dict()
        for f in self._ctx.files:
            if not isinstance(namespace, SfgGlobalNamespace):
                block = SfgNamespaceBlock(
                    self._cur_namespace, self._cur_namespace.fqname
                )
                f.elements.append(block)
                self._loc[f] = block.elements
            else:
                self._loc[f] = f.elements

    @property
    def current_namespace(self) -> SfgNamespace:
        return self._cur_namespace

    def get_entity(self, name: str) -> SfgCodeEntity | None:
        return self._cur_namespace.get_entity(name)

    def add_entity(self, entity: SfgCodeEntity):
        self._cur_namespace.add_entity(entity)

    def write_header(self, elem: SfgNamespaceElement) -> None:
        self._loc[self._ctx.header_file].append(elem)

    def write_impl(self, elem: SfgNamespaceElement) -> None:
        impl_file = self._ctx.impl_file
        if impl_file is None:
            raise SfgException(
                f"Cannot write element {elem} to implemenation file since no implementation file is being generated."
            )
        self._loc[impl_file].append(elem)

    def enter_namespace(self, qual_name: str):
        namespace = self._cur_namespace.get_child_namespace(qual_name)

        outer_locs = self._loc.copy()

        for f in self._ctx.files:
            block = SfgNamespaceBlock(namespace, qual_name)
            self._loc[f].append(block)
            self._loc[f] = block.elements

        @contextmanager
        def ctxmgr():
            try:
                yield None
            finally:
                #   Have the cursor step back out of the nested namespace blocks
                self._loc = outer_locs

        return ctxmgr()
