import pytest

from pystencilssfg import SfgException
from pystencilssfg.lang import asvar, SfgVar, AugExpr

import sympy as sp

from pystencils import TypedSymbol, DynamicType


def test_asvar():
    #   SfgVar must be returned as-is
    var = SfgVar("p", "uint64")
    assert var is asvar(var)

    #   TypedSymbol is transformed
    ts = TypedSymbol("q", "int32")
    assert asvar(ts) == SfgVar("q", "int32")

    #   Variable AugExprs get lowered to SfgVar
    augexpr = AugExpr("uint16").var("l")
    assert asvar(augexpr) == SfgVar("l", "uint16")

    #   Complex AugExprs cannot be parsed
    cexpr = AugExpr.format("{} + {}", SfgVar("m", "int32"), AugExpr("int32").var("n"))
    with pytest.raises(SfgException):
        _ = asvar(cexpr)

    #   Untyped SymPy symbols won't be parsed
    x = sp.Symbol("x")
    with pytest.raises(ValueError):
        _ = asvar(x)

    #   Dynamically typed TypedSymbols cannot be parsed
    y = TypedSymbol("y", DynamicType.NUMERIC_TYPE)
    with pytest.raises(ValueError):
        _ = asvar(y)


def test_augexpr_format():
    expr = AugExpr.format("std::vector< real_t > {{ 0.1, 0.2, 0.3 }}")
    assert expr.code == "std::vector< real_t > { 0.1, 0.2, 0.3 }"
    assert not expr.depends

    expr = AugExpr("int").var("p")
    assert expr.code == "p"
    assert expr.depends == {SfgVar("p", "int")}

    expr = AugExpr.format(
        "{} + {} / {}",
        AugExpr("int").var("p"),
        AugExpr("int").var("q"),
        AugExpr("uint32").var("r"),
    )

    assert str(expr) == expr.code == "p + q / r"

    assert expr.depends == {
        SfgVar("p", "int"),
        SfgVar("q", "int"),
        SfgVar("r", "uint32"),
    }

    #   Must find TypedSymbols as dependencies
    expr = AugExpr.format(
        "{} + {} / {}",
        AugExpr("int").var("p"),
        TypedSymbol("x", "int32"),
        TypedSymbol("y", "int32"),
    )

    assert expr.code == "p + x / y"
    assert expr.depends == {
        SfgVar("p", "int"),
        SfgVar("x", "int32"),
        SfgVar("y", "int32"),
    }

    #   Can parse constant SymPy expressions
    expr = AugExpr.format("{}", sp.sympify(1))

    assert expr.code == "1"
    assert not expr.depends


def test_augexpr_illegal_format():
    x, y, z = sp.symbols("x, y, z")

    with pytest.raises(ValueError):
        #   Cannot parse SymPy symbols
        _ = AugExpr.format("{}", x)

    with pytest.raises(ValueError):
        #   Cannot parse expressions containing symbols
        _ = AugExpr.format("{} + {}", x + 3, y / (2 * z))
