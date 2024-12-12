import pytest

import pystencils as ps

from pystencilssfg.lang.cpp import std
from pystencilssfg.lang import includes, HeaderFile


def no_spaces(s: str):
    return "".join(s.split())


def test_stl_containers():
    expr = std.vector("float64").var("numbers")
    assert no_spaces(expr.get_dtype().c_string()) == "std::vector<double>"
    assert includes(expr) == {HeaderFile.parse("<vector>")}

    expr = std.vector("float64", ref=True, const=True).var("numbers")
    assert no_spaces(expr.get_dtype().c_string()) == "conststd::vector<double>&"
    assert includes(expr) == {HeaderFile.parse("<vector>")}

    expr = std.tuple(("float64", "int32", "uint16", "bool")).var("t")
    assert (
        no_spaces(expr.get_dtype().c_string())
        == "std::tuple<double,int32_t,uint16_t,bool>"
    )
    assert includes(expr) == {HeaderFile.parse("<tuple>")}

    expr = std.span("uint16", ref=True).var("s")
    assert no_spaces(expr.get_dtype().c_string()) == "std::span<uint16_t>&"
    assert includes(expr) == {HeaderFile.parse("<span>")}


def test_vector_from_field():
    f = ps.fields("f: float32[1D]")
    f_vec = std.vector.from_field(f)

    assert f_vec.element_type == ps.create_type("float32")
    assert str(f_vec) == f.name

    f = ps.fields("f(1): float32[1D]")
    f_vec = std.vector.from_field(f)

    assert f_vec.element_type == ps.create_type("float32")
    assert str(f_vec) == f.name

    f = ps.fields("f(2): float32[1D]")
    with pytest.raises(ValueError):
        std.vector.from_field(f)

    f = ps.fields("f(1): float32[2D]")
    with pytest.raises(ValueError):
        std.vector.from_field(f)


def test_span_from_field():
    f = ps.fields("f: float32[1D]")
    f_vec = std.span.from_field(f)

    assert f_vec.element_type == ps.create_type("float32")
    assert str(f_vec) == f.name

    f = ps.fields("f(1): float32[1D]")
    f_vec = std.span.from_field(f)

    assert f_vec.element_type == ps.create_type("float32")
    assert str(f_vec) == f.name

    f = ps.fields("f(2): float32[1D]")
    with pytest.raises(ValueError):
        std.span.from_field(f)

    f = ps.fields("f(1): float32[2D]")
    with pytest.raises(ValueError):
        std.span.from_field(f)
