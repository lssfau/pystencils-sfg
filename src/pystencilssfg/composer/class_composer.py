from __future__ import annotations
from typing import Sequence

from pystencils.types import PsCustomType, UserTypeSpec, create_type

from ..lang import (
    _VarLike,
    VarLike,
    ExprLike,
    asvar,
    SfgVar,
)

from ..ir.source_components import (
    SfgClass,
    SfgClassMember,
    SfgInClassDefinition,
    SfgConstructor,
    SfgMethod,
    SfgMemberVariable,
    SfgClassKeyword,
    SfgVisibility,
    SfgVisibilityBlock,
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

    class VisibilityContext:
        """Represent a visibility block in the composer syntax.

        Returned by `private`, `public`, and `protected`.
        """

        def __init__(self, visibility: SfgVisibility):
            self._vis_block = SfgVisibilityBlock(visibility)

        def members(self):
            yield from self._vis_block.members()

        def __call__(
            self,
            *args: (
                SfgClassMember | SfgClassComposer.ConstructorBuilder | VarLike | str
            ),
        ):
            for arg in args:
                self._vis_block.append_member(SfgClassComposer._resolve_member(arg))

            return self

        def resolve(self, cls: SfgClass) -> None:
            cls.append_visibility_block(self._vis_block)

    class ConstructorBuilder:
        """Composer syntax for constructor building.

        Returned by `constructor`.
        """

        def __init__(self, *params: VarLike):
            self._params = list(asvar(p) for p in params)
            self._initializers: list[str] = []
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
                expr = ", ".join(str(arg) for arg in args)
                initializer = f"{member}{{ {expr} }}"
                self._initializers.append(initializer)
                return self

            return init_sequencer

        def body(self, body: str):
            """Define the constructor body"""
            if self._body is not None:
                raise SfgException("Multiple definitions of constructor body.")
            self._body = body
            return self

        def resolve(self) -> SfgConstructor:
            return SfgConstructor(
                parameters=self._params,
                initializers=self._initializers,
                body=self._body if self._body is not None else "",
            )

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

    @property
    def public(self) -> SfgClassComposer.VisibilityContext:
        """Create a `public` visibility block in a class body"""
        return SfgClassComposer.VisibilityContext(SfgVisibility.PUBLIC)

    @property
    def protected(self) -> SfgClassComposer.VisibilityContext:
        """Create a `protected` visibility block in a class or struct body"""
        return SfgClassComposer.VisibilityContext(SfgVisibility.PROTECTED)

    @property
    def private(self) -> SfgClassComposer.VisibilityContext:
        """Create a `private` visibility block in a class or struct body"""
        return SfgClassComposer.VisibilityContext(SfgVisibility.PRIVATE)

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

        def sequencer(*args: SequencerArg):
            tree = make_sequence(*args)
            return SfgMethod(
                name,
                tree,
                return_type=create_type(returns),
                inline=inline,
                const=const,
            )

        return sequencer

    #   INTERNALS

    def _class(self, class_name: str, keyword: SfgClassKeyword, bases: Sequence[str]):
        if self._ctx.get_class(class_name) is not None:
            raise ValueError(f"Class or struct {class_name} already exists.")

        cls = SfgClass(class_name, class_keyword=keyword, bases=bases)
        self._ctx.add_class(cls)

        def sequencer(
            *args: (
                SfgClassComposer.VisibilityContext
                | SfgClassMember
                | SfgClassComposer.ConstructorBuilder
                | VarLike
                | str
            ),
        ):
            default_ended = False

            for arg in args:
                if isinstance(arg, SfgClassComposer.VisibilityContext):
                    default_ended = True
                    arg.resolve(cls)
                elif isinstance(
                    arg,
                    (
                        SfgClassMember,
                        SfgClassComposer.ConstructorBuilder,
                        str,
                    )
                    + _VarLike,
                ):
                    if default_ended:
                        raise SfgException(
                            "Composer Syntax Error: "
                            "Cannot add members with default visibility after a visibility block."
                        )
                    else:
                        cls.default.append_member(self._resolve_member(arg))
                else:
                    raise SfgException(f"{arg} is not a valid class member.")

        return sequencer

    @staticmethod
    def _resolve_member(
        arg: SfgClassMember | SfgClassComposer.ConstructorBuilder | VarLike | str,
    ) -> SfgClassMember:
        match arg:
            case _ if isinstance(arg, _VarLike):
                var = asvar(arg)
                return SfgMemberVariable(var.name, var.dtype)
            case str():
                return SfgInClassDefinition(arg)
            case SfgClassComposer.ConstructorBuilder():
                return arg.resolve()
            case SfgClassMember():
                return arg
            case _:
                raise ValueError(f"Invalid class member: {arg}")
