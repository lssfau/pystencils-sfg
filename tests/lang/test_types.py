from pystencilssfg.lang import cpptype, HeaderFile
from pystencils import create_type


def test_cpptypes():
    tclass = cpptype("std::vector< {T}, {Allocator} >", "<vector>")

    vec_type = tclass(T=create_type("float32"), Allocator="std::allocator< float >")
    assert str(vec_type).strip() == "std::vector< float, std::allocator< float > >"
    assert (
        tclass.includes
        == vec_type.includes
        == {HeaderFile("vector", system_header=True)}
    )
