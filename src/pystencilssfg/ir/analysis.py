from __future__ import annotations
from typing import Any

from functools import reduce

from ..exceptions import SfgException
from ..lang import HeaderFile, includes


def collect_includes(obj: Any) -> set[HeaderFile]:
    from ..context import SfgContext
    from .call_tree import SfgCallTreeNode
    from .source_components import (
        SfgFunction,
        SfgClass,
        SfgConstructor,
        SfgMemberVariable,
        SfgInClassDefinition,
    )

    match obj:
        case SfgContext():
            headers = set()
            for func in obj.functions():
                headers |= collect_includes(func)

            for cls in obj.classes():
                headers |= collect_includes(cls)

            return headers

        case SfgCallTreeNode():
            return reduce(
                lambda accu, child: accu | collect_includes(child),
                obj.children,
                obj.required_includes,
            )

        case SfgFunction(_, tree, parameters):
            param_headers: set[HeaderFile] = reduce(
                set.union, (includes(p) for p in parameters), set()
            )
            return param_headers | collect_includes(tree)

        case SfgClass():
            return reduce(
                lambda accu, member: accu | (collect_includes(member)),
                obj.members(),
                set(),
            )

        case SfgConstructor(parameters):
            param_headers = reduce(
                set.union, (includes(p) for p in parameters), set()
            )
            return param_headers

        case SfgMemberVariable():
            return includes(obj)

        case SfgInClassDefinition():
            return set()

        case _:
            raise SfgException(
                f"Can't collect includes from object of type {type(obj)}"
            )
