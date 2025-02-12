from __future__ import annotations

from enum import Enum, auto
from typing import (
    Iterable,
    TypeVar,
    Generic,
)

from ..lang import HeaderFile

from .entities import (
    SfgNamespace,
    SfgKernelHandle,
    SfgFunction,
    SfgClassMember,
    SfgVisibility,
    SfgClass,
)

#   =========================================================================================================
#
#   SYNTACTICAL ELEMENTS
#
#   These classes model *code elements*, which represent the actual syntax objects that populate the output
#   files, their namespaces and class bodies.
#
#   =========================================================================================================


SourceEntity_T = TypeVar(
    "SourceEntity_T",
    bound=SfgKernelHandle | SfgFunction | SfgClassMember | SfgClass,
    covariant=True,
)
"""Source entities that may have declarations and definitions."""


class SfgEntityDecl(Generic[SourceEntity_T]):
    """Declaration of a function, class, method, or constructor"""

    __match_args__ = ("entity",)

    def __init__(self, entity: SourceEntity_T) -> None:
        self._entity = entity

    @property
    def entity(self) -> SourceEntity_T:
        return self._entity


class SfgEntityDef(Generic[SourceEntity_T]):
    """Definition of a function, class, method, or constructor"""

    __match_args__ = ("entity",)

    def __init__(self, entity: SourceEntity_T) -> None:
        self._entity = entity

    @property
    def entity(self) -> SourceEntity_T:
        return self._entity


SfgClassBodyElement = str | SfgEntityDecl[SfgClassMember] | SfgEntityDef[SfgClassMember]
"""Elements that may be placed in the visibility blocks of a class body."""


class SfgVisibilityBlock:
    """Visibility-qualified block inside a class definition body.

    Visibility blocks host the code elements placed inside a class body:
    method and constructor declarations,
    in-class method and constructor definitions,
    as well as variable declarations and definitions.

    Args:
        visibility: The visibility qualifier of this block
    """

    __match_args__ = ("visibility", "elements")

    def __init__(self, visibility: SfgVisibility) -> None:
        self._vis = visibility
        self._elements: list[SfgClassBodyElement] = []
        self._cls: SfgClass | None = None

    @property
    def visibility(self) -> SfgVisibility:
        return self._vis

    @property
    def elements(self) -> list[SfgClassBodyElement]:
        return self._elements

    @elements.setter
    def elements(self, elems: Iterable[SfgClassBodyElement]):
        self._elements = list(elems)


class SfgNamespaceBlock:
    """A C++ namespace block.

    Args:
        namespace: Namespace associated with this block
        label: Label printed at the opening brace of this block.
            This may be the namespace name, or a compressed qualified
            name containing one or more of its parent namespaces.
    """

    __match_args__ = (
        "namespace",
        "elements",
        "label",
    )

    def __init__(self, namespace: SfgNamespace, label: str | None = None) -> None:
        self._namespace = namespace
        self._label = label if label is not None else namespace.name
        self._elements: list[SfgNamespaceElement] = []

    @property
    def namespace(self) -> SfgNamespace:
        return self._namespace

    @property
    def label(self) -> str:
        return self._label

    @property
    def elements(self) -> list[SfgNamespaceElement]:
        """Sequence of source elements that make up the body of this namespace"""
        return self._elements

    @elements.setter
    def elements(self, elems: Iterable[SfgNamespaceElement]):
        self._elements = list(elems)


class SfgClassBody:
    """Body of a class definition."""

    __match_args__ = ("associated_class", "visibility_blocks")

    def __init__(
        self,
        cls: SfgClass,
        default_block: SfgVisibilityBlock,
        vis_blocks: Iterable[SfgVisibilityBlock],
    ) -> None:
        self._cls = cls
        assert default_block.visibility == SfgVisibility.DEFAULT
        self._default_block = default_block
        self._blocks = [self._default_block] + list(vis_blocks)

    @property
    def associated_class(self) -> SfgClass:
        return self._cls

    @property
    def default(self) -> SfgVisibilityBlock:
        return self._default_block

    def append_visibility_block(self, block: SfgVisibilityBlock):
        if block.visibility == SfgVisibility.DEFAULT:
            raise ValueError(
                "Can't add another block with DEFAULT visibility to this class body."
            )
        self._blocks.append(block)

    @property
    def visibility_blocks(self) -> tuple[SfgVisibilityBlock, ...]:
        return tuple(self._blocks)


SfgNamespaceElement = (
    str | SfgNamespaceBlock | SfgClassBody | SfgEntityDecl | SfgEntityDef
)
"""Elements that may be placed inside a namespace, including the global namespace."""


class SfgSourceFileType(Enum):
    HEADER = auto()
    TRANSLATION_UNIT = auto()


class SfgSourceFile:
    """A C++ source file.

    Args:
        name: Name of the file (without parent directories), e.g. ``Algorithms.cpp``
        file_type: Type of the source file (header or translation unit)
        prelude: Optionally, text of the prelude comment printed at the top of the file
    """

    def __init__(
        self, name: str, file_type: SfgSourceFileType, prelude: str | None = None
    ) -> None:
        self._name: str = name
        self._file_type: SfgSourceFileType = file_type
        self._prelude: str | None = prelude
        self._includes: list[HeaderFile] = []
        self._elements: list[SfgNamespaceElement] = []

    @property
    def name(self) -> str:
        """Name of this source file"""
        return self._name

    @property
    def file_type(self) -> SfgSourceFileType:
        """File type of this source file"""
        return self._file_type

    @property
    def prelude(self) -> str | None:
        """Text of the prelude comment"""
        return self._prelude

    @prelude.setter
    def prelude(self, text: str | None):
        self._prelude = text

    @property
    def includes(self) -> list[HeaderFile]:
        """Sequence of header files to be included at the top of this file"""
        return self._includes

    @includes.setter
    def includes(self, incl: Iterable[HeaderFile]):
        self._includes = list(incl)

    @property
    def elements(self) -> list[SfgNamespaceElement]:
        """Sequence of source elements comprising the body of this file"""
        return self._elements

    @elements.setter
    def elements(self, elems: Iterable[SfgNamespaceElement]):
        self._elements = list(elems)
