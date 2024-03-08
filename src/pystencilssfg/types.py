from typing import Union, TypeAlias, NewType
import numpy as np

from pystencils.typing import AbstractType, numpy_name_to_c


PsType: TypeAlias = Union[type, np.dtype, AbstractType]
"""Types used in interacting with pystencils.

PsType represents various ways of specifying types within pystencils.
In particular, it encompasses most ways to construct an instance of `AbstractType`,
for example via `create_type`.

(Note that, while `create_type` does accept strings, they are excluded here for
reasons of safety. It is discouraged to use strings for type specifications when working
with pystencils!)

PsType is a temporary solution and will be removed in the future
in favor of the consolidated pystencils backend typing system.
"""

SrcType = NewType("SrcType", str)
"""C/C++-Types occuring during source file generation.

When necessary, the SFG package checks equality of types by their name strings; it does
not care about typedefs, aliases, namespaces, etc!

SrcType is a temporary solution and will be removed in the future
in favor of the consolidated pystencils backend typing system.
"""


def cpp_typename(type_obj: Union[str, SrcType, PsType]):
    """Accepts type specifications in various ways and returns a valid typename to be used in code."""
    # if isinstance(type_obj, str):
    #     return type_obj
    if isinstance(type_obj, str):
        return type_obj
    elif isinstance(type_obj, AbstractType):
        return str(type_obj)
    elif isinstance(type_obj, np.dtype) or isinstance(type_obj, type):
        return numpy_name_to_c(np.dtype(type_obj).name)
    else:
        raise ValueError(f"Don't know how to interpret type object {type_obj}.")
