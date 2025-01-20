import pytest

from pystencilssfg.lang import cpptype, HeaderFile, Ref, strip_ptr_ref
from pystencils import create_type
from pystencils.types import constify, deconstify


def test_cpptypes():
    tfactory = cpptype("std::vector< {}, {} >", "<vector>")

    vec_type = tfactory(create_type("float32"), "std::allocator< float >")
    assert str(vec_type).strip() == "std::vector< float, std::allocator< float > >"
    assert (
        vec_type.includes
        == {HeaderFile("vector", system_header=True)}
    )

    #   Cloning
    assert deconstify(constify(vec_type)) == vec_type

    #   Duplicate Equality
    assert tfactory(create_type("float32"), "std::allocator< float >") == vec_type
    #   Not equal with different argument even though it produces the same string
    assert tfactory("float", "std::allocator< float >") != vec_type

    #   The same with keyword arguments
    tfactory = cpptype("std::vector< {T}, {Allocator} >", "<vector>")

    vec_type = tfactory(T=create_type("float32"), Allocator="std::allocator< float >")
    assert str(vec_type).strip() == "std::vector< float, std::allocator< float > >"

    assert deconstify(constify(vec_type)) == vec_type


def test_cpptype_invalid_construction():
    tfactory = cpptype("std::vector< {}, {Allocator} >", "<vector>")

    with pytest.raises(IndexError):
        _ = tfactory(Allocator="SomeAlloc")

    with pytest.raises(KeyError):
        _ = tfactory("int")

    with pytest.raises(ValueError, match="Too many positional arguments"):
        _ = tfactory("int", "bogus", Allocator="SomeAlloc")

    with pytest.raises(ValueError, match="Extraneous keyword arguments"):
        _ = tfactory("int", Allocator="SomeAlloc", bogus=2)


def test_cpptype_const():
    tfactory = cpptype("std::vector< {T} >", "<vector>")

    vec_type = tfactory(T=create_type("uint32"))
    assert constify(vec_type) == tfactory(T=create_type("uint32"), const=True)

    vec_type = tfactory(T=create_type("uint32"), const=True)
    assert deconstify(vec_type) == tfactory(T=create_type("uint32"), const=False)


def test_cpptype_ref():
    tfactory = cpptype("std::vector< {T} >", "<vector>")

    vec_type = tfactory(T=create_type("uint32"), ref=True)
    assert isinstance(vec_type, Ref)
    assert strip_ptr_ref(vec_type) == tfactory(T=create_type("uint32"))


def test_cpptype_inherits_headers():
    optional_tfactory = cpptype("std::optional< {T} >", "<optional>")
    vec_tfactory = cpptype("std::vector< {T} >", "<vector>")

    vec_type = vec_tfactory(T=optional_tfactory(T="int"))
    assert vec_type.includes == {
        HeaderFile.parse("<optional>"),
        HeaderFile.parse("<vector>"),
    }
