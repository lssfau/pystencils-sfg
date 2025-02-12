from __future__ import annotations

from ..lang import HeaderFile, includes
from .syntax import (
    SfgSourceFile,
    SfgNamespaceElement,
    SfgClassBodyElement,
    SfgNamespaceBlock,
    SfgEntityDecl,
    SfgEntityDef,
    SfgClassBody,
    SfgVisibilityBlock,
)


def collect_includes(file: SfgSourceFile) -> set[HeaderFile]:
    from .call_tree import SfgCallTreeNode
    from .entities import (
        SfgCodeEntity,
        SfgKernelHandle,
        SfgFunction,
        SfgMethod,
        SfgClassMember,
        SfgConstructor,
        SfgMemberVariable,
    )

    def visit_decl(entity: SfgCodeEntity | SfgClassMember) -> set[HeaderFile]:
        match entity:
            case (
                SfgKernelHandle(_, parameters)
                | SfgFunction(_, _, parameters)
                | SfgMethod(_, _, parameters)
                | SfgConstructor(_, parameters, _, _)
            ):
                incls: set[HeaderFile] = set().union(*(includes(p) for p in parameters))
                if isinstance(entity, (SfgFunction, SfgMethod)):
                    incls |= includes(entity.return_type)
                return incls

            case SfgMemberVariable():
                return includes(entity)

            case _:
                assert False, "unexpected entity"

    def walk_syntax(
        obj: (
            SfgNamespaceElement
            | SfgClassBodyElement
            | SfgVisibilityBlock
            | SfgCallTreeNode
        ),
    ) -> set[HeaderFile]:
        match obj:
            case str():
                return set()

            case SfgCallTreeNode():
                return obj.required_includes.union(
                    *(walk_syntax(child) for child in obj.children),
                )

            case SfgEntityDecl(entity):
                return visit_decl(entity)

            case SfgEntityDef(entity):
                match entity:
                    case SfgKernelHandle(kernel, _):
                        return (
                            set(HeaderFile.parse(h) for h in kernel.required_headers)
                            | {HeaderFile.parse("<cstdint>")}
                            | visit_decl(entity)
                        )

                    case SfgFunction(_, tree, _) | SfgMethod(_, tree, _):
                        return walk_syntax(tree) | visit_decl(entity)

                    case SfgConstructor():
                        return visit_decl(entity)

                    case SfgMemberVariable():
                        return includes(entity)

                    case _:
                        assert False, "unexpected entity"

            case SfgNamespaceBlock(_, elements) | SfgVisibilityBlock(_, elements):
                return set().union(*(walk_syntax(elem) for elem in elements))  # type: ignore

            case SfgClassBody(_, vblocks):
                return set().union(*(walk_syntax(vb) for vb in vblocks))

            case _:
                assert False, "unexpected syntax element"

    return set().union(*(walk_syntax(elem) for elem in file.elements))
