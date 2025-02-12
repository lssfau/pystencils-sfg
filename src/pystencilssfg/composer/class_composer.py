from __future__ import annotations
from typing import Sequence
from itertools import takewhile, dropwhile
import numpy as np

from pystencils.types import PsCustomType, UserTypeSpec, create_type

from ..context import SfgContext
from ..lang import (
    VarLike,
    ExprLike,
    asvar,
    SfgVar,
)

from ..ir import (
    SfgCallTreeNode,
    SfgClass,
    SfgConstructor,
    SfgMethod,
    SfgMemberVariable,
    SfgClassKeyword,
    SfgVisibility,
    SfgVisibilityBlock,
    SfgEntityDecl,
    SfgEntityDef,
    SfgClassBody,
)
from ..exceptions import SfgException

from .mixin import SfgComposerMixIn
from .basic_composer import (
    make_sequence,
    SequencerArg,
)


class SfgClassComposer(SfgComposerMixIn):
    """Composer for classes and structs.


    This class cannot be instantiated on its own but must be mixed in with
    :class:`SfgBasicComposer`.
    Its interface is exposed by :class:`SfgComposer`.
    """

    class VisibilityBlockSequencer:
        """Represent a visibility block in the composer syntax.

        Returned by `private`, `public`, and `protected`.
        """

        def __init__(self, visibility: SfgVisibility):
            self._visibility = visibility
            self._args: tuple[
                SfgClassComposer.MethodSequencer
                | SfgClassComposer.ConstructorBuilder
                | VarLike
                | str,
                ...,
            ]

        def __call__(
            self,
            *args: (
                SfgClassComposer.MethodSequencer
                | SfgClassComposer.ConstructorBuilder
                | VarLike
                | str
            ),
        ):
            self._args = args
            return self

        def _resolve(self, ctx: SfgContext, cls: SfgClass) -> SfgVisibilityBlock:
            vis_block = SfgVisibilityBlock(self._visibility)
            for arg in self._args:
                match arg:
                    case (
                        SfgClassComposer.MethodSequencer()
                        | SfgClassComposer.ConstructorBuilder()
                    ):
                        arg._resolve(ctx, cls, vis_block)
                    case str():
                        vis_block.elements.append(arg)
                    case _:
                        var = asvar(arg)
                        member_var = SfgMemberVariable(var.name, var.dtype, cls)
                        cls.add_member(member_var, vis_block.visibility)
                        vis_block.elements.append(SfgEntityDef(member_var))
            return vis_block

    class MethodSequencer:
        def __init__(
            self,
            name: str,
            returns: UserTypeSpec = PsCustomType("void"),
            inline: bool = False,
            const: bool = False,
        ) -> None:
            self._name = name
            self._returns = create_type(returns)
            self._inline = inline
            self._const = const
            self._tree: SfgCallTreeNode

        def __call__(self, *args: SequencerArg):
            self._tree = make_sequence(*args)
            return self

        def _resolve(
            self, ctx: SfgContext, cls: SfgClass, vis_block: SfgVisibilityBlock
        ):
            method = SfgMethod(
                self._name,
                cls,
                self._tree,
                return_type=self._returns,
                inline=self._inline,
                const=self._const,
            )
            cls.add_member(method, vis_block.visibility)

            if self._inline:
                vis_block.elements.append(SfgEntityDef(method))
            else:
                vis_block.elements.append(SfgEntityDecl(method))
                ctx._cursor.write_impl(SfgEntityDef(method))

    class ConstructorBuilder:
        """Composer syntax for constructor building.

        Returned by `constructor`.
        """

        def __init__(self, *params: VarLike):
            self._params = list(asvar(p) for p in params)
            self._initializers: list[tuple[SfgVar | str, tuple[ExprLike, ...]]] = []
            self._body: str | None = None

        def add_param(self, param: VarLike, at: int | None = None):
            if at is None:
                self._params.append(asvar(param))
            else:
                self._params.insert(at, asvar(param))

        @property
        def parameters(self) -> list[SfgVar]:
            return self._params

        def init(self, var: VarLike | str):
            """Add an initialization expression to the constructor's initializer list."""

            member = var if isinstance(var, str) else asvar(var)

            def init_sequencer(*args: ExprLike):
                self._initializers.append((member, args))
                return self

            return init_sequencer

        def body(self, body: str):
            """Define the constructor body"""
            if self._body is not None:
                raise SfgException("Multiple definitions of constructor body.")
            self._body = body
            return self

        def _resolve(
            self, ctx: SfgContext, cls: SfgClass, vis_block: SfgVisibilityBlock
        ):
            ctor = SfgConstructor(
                cls,
                parameters=self._params,
                initializers=self._initializers,
                body=self._body if self._body is not None else "",
            )

            cls.add_member(ctor, vis_block.visibility)
            vis_block.elements.append(SfgEntityDef(ctor))

    def klass(self, class_name: str, bases: Sequence[str] = ()):
        """Create a class and add it to the underlying context.

        Args:
            class_name: Name of the class
            bases: List of base classes
        """
        return self._class(class_name, SfgClassKeyword.CLASS, bases)

    def struct(self, class_name: str, bases: Sequence[str] = ()):
        """Create a struct and add it to the underlying context.

        Args:
            class_name: Name of the struct
            bases: List of base classes
        """
        return self._class(class_name, SfgClassKeyword.STRUCT, bases)

    def numpy_struct(
        self, name: str, dtype: np.dtype, add_constructor: bool = True
    ):
        """Add a numpy structured data type as a C++ struct

        Returns:
            The created class object
        """
        return self._struct_from_numpy_dtype(name, dtype, add_constructor)

    @property
    def public(self) -> SfgClassComposer.VisibilityBlockSequencer:
        """Create a `public` visibility block in a class body"""
        return SfgClassComposer.VisibilityBlockSequencer(SfgVisibility.PUBLIC)

    @property
    def protected(self) -> SfgClassComposer.VisibilityBlockSequencer:
        """Create a `protected` visibility block in a class or struct body"""
        return SfgClassComposer.VisibilityBlockSequencer(SfgVisibility.PROTECTED)

    @property
    def private(self) -> SfgClassComposer.VisibilityBlockSequencer:
        """Create a `private` visibility block in a class or struct body"""
        return SfgClassComposer.VisibilityBlockSequencer(SfgVisibility.PRIVATE)

    def constructor(self, *params: VarLike):
        """In a class or struct body or visibility block, add a constructor.

        Args:
            params: List of constructor parameters
        """
        return SfgClassComposer.ConstructorBuilder(*params)

    def method(
        self,
        name: str,
        returns: UserTypeSpec = PsCustomType("void"),
        inline: bool = False,
        const: bool = False,
    ):
        """In a class or struct body or visibility block, add a method.
        The usage is similar to :any:`SfgBasicComposer.function`.

        Args:
            name: The method name
            returns: The method's return type
            inline: Whether or not the method should be defined in-line.
            const: Whether or not the method is const-qualified.
        """

        return SfgClassComposer.MethodSequencer(name, returns, inline, const)

    #   INTERNALS

    def _class(self, class_name: str, keyword: SfgClassKeyword, bases: Sequence[str]):
        #   TODO: Return a `CppClass` instance representing the generated class

        if self._cursor.get_entity(class_name) is not None:
            raise ValueError(
                f"Another entity with name {class_name} already exists in the current namespace."
            )

        cls = SfgClass(
            class_name,
            self._cursor.current_namespace,
            class_keyword=keyword,
            bases=bases,
        )
        self._cursor.add_entity(cls)

        def sequencer(
            *args: (
                SfgClassComposer.VisibilityBlockSequencer
                | SfgClassComposer.MethodSequencer
                | SfgClassComposer.ConstructorBuilder
                | VarLike
                | str
            ),
        ):
            default_vis_sequencer = SfgClassComposer.VisibilityBlockSequencer(
                SfgVisibility.DEFAULT
            )

            def argfilter(arg):
                return not isinstance(arg, SfgClassComposer.VisibilityBlockSequencer)

            default_vis_args = takewhile(
                argfilter,
                args,
            )
            default_block = default_vis_sequencer(*default_vis_args)._resolve(self._ctx, cls)  # type: ignore
            vis_blocks: list[SfgVisibilityBlock] = []

            for arg in dropwhile(argfilter, args):
                if isinstance(arg, SfgClassComposer.VisibilityBlockSequencer):
                    vis_blocks.append(arg._resolve(self._ctx, cls))
                else:
                    raise SfgException(
                        "Composer Syntax Error: "
                        "Cannot add members with default visibility after a visibility block."
                    )

            self._cursor.write_header(SfgClassBody(cls, default_block, vis_blocks))

        return sequencer

    def _struct_from_numpy_dtype(
        self, struct_name: str, dtype: np.dtype, add_constructor: bool = True
    ):
        fields = dtype.fields
        if fields is None:
            raise SfgException(f"Numpy dtype {dtype} is not a structured type.")

        members: list[SfgClassComposer.ConstructorBuilder | SfgVar] = []
        if add_constructor:
            ctor = self.constructor()
            members.append(ctor)

        for member_name, type_info in fields.items():
            member_type = create_type(type_info[0])

            member = SfgVar(member_name, member_type)
            members.append(member)

            if add_constructor:
                arg = SfgVar(f"{member_name}_", member_type)
                ctor.add_param(arg)
                ctor.init(member)(arg)

        return self.struct(
            struct_name,
        )(*members)
