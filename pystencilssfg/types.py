from pystencils.typing import AbstractType, BasicType, StructType, PointerType


class SrcType:
    """Valid C/C++-Type occuring during source file generation.

    Nonprimitive C/C++ types are represented by their names.
    When necessary, the SFG package checks equality of types by these name strings; it does
    not care about typedefs, aliases, namespaces, etc!
    """
    

