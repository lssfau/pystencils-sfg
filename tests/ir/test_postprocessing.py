import sympy as sp
from pystencils import (
    fields,
    kernel,
    TypedSymbol,
    Field,
    FieldType,
    create_type,
    Assignment,
)
from pystencils.types import PsCustomType

from pystencilssfg.composer import make_sequence

from pystencilssfg.lang import AugExpr, SupportsFieldExtraction
from pystencilssfg.lang.cpp import std

from pystencilssfg.ir import SfgStatements, SfgSequence
from pystencilssfg.ir.postprocessing import CallTreePostProcessing


def test_live_vars(sfg):
    f, g = fields("f, g(2): double[2D]")
    x, y = [TypedSymbol(n, "double") for n in "xy"]
    z = sp.Symbol("z")

    @kernel
    def update():
        f[0, 0] @= x * g.center(0) + y * g.center(1) - z

    khandle = sfg.kernels.create(update)

    a = sfg.var("a", "float")
    b = sfg.var("b", "float")

    call_tree = make_sequence(
        sfg.init(x)(a), sfg.init(y)(sfg.expr("{} - {}", b, x)), sfg.call(khandle)  #  #
    )

    pp = CallTreePostProcessing()
    free_vars = pp.get_live_variables(call_tree)

    expected = {a.as_variable(), b.as_variable()} | set(
        param for param in khandle.parameters if param.name not in "xy"
    )

    assert free_vars == expected


def test_find_sympy_symbols(sfg):
    f, g = fields("f, g(2): double[2D]")
    x, y, z = sp.symbols("x, y, z")

    @kernel
    def update():
        f[0, 0] @= x * g.center(0) + y * g.center(1) - z

    khandle = sfg.kernels.create(update)

    a = sfg.var("a", "double")
    b = sfg.var("b", "double")

    call_tree = make_sequence(
        sfg.set_param(x, b),
        sfg.set_param(y, sfg.expr("{} / {}", x.name, a)),
        sfg.call(khandle),
    )

    pp = CallTreePostProcessing()
    live_vars = pp.get_live_variables(call_tree)

    expected = {a.as_variable(), b.as_variable()} | set(
        param for param in khandle.parameters if param.name not in "xy"
    )

    assert live_vars == expected

    assert isinstance(call_tree.children[0], SfgStatements)
    assert call_tree.children[0].code_string == "const double x = b;"

    assert isinstance(call_tree.children[1], SfgStatements)
    assert call_tree.children[1].code_string == "const double y = x / a;"


class DemoFieldExtraction(SupportsFieldExtraction):
    def __init__(self, name: str):
        self.obj = AugExpr(PsCustomType("MyField")).var(name)

    def _extract_ptr(self) -> AugExpr:
        return AugExpr.format("{}.ptr()", self.obj)

    def _extract_size(self, coordinate: int) -> AugExpr | None:
        return AugExpr.format("{}.size({})", self.obj, coordinate)

    def _extract_stride(self, coordinate: int) -> AugExpr | None:
        return AugExpr.format("{}.stride({})", self.obj, coordinate)


def test_field_extraction(sfg):
    sx, sy, tx, ty = [
        TypedSymbol(n, create_type("int64")) for n in ("sx", "sy", "tx", "ty")
    ]
    f = Field("f", FieldType.GENERIC, "double", (1, 0), (sx, sy), (tx, ty))

    @kernel
    def set_constant():
        f.center @= 13.2

    khandle = sfg.kernels.create(set_constant)

    extraction = DemoFieldExtraction("f")
    call_tree = make_sequence(
        sfg.map_field(f, extraction, cast_indexing_symbols=False), sfg.call(khandle)
    )

    pp = CallTreePostProcessing()
    free_vars = pp.get_live_variables(call_tree)
    assert free_vars == {extraction.obj.as_variable()}

    lines = [
        r"double * RESTRICT const _data_f { f.ptr() };",
        r"const int64_t sx { f.size(0) };",
        r"const int64_t sy { f.size(1) };",
        r"const int64_t tx { f.stride(0) };",
        r"const int64_t ty { f.stride(1) };",
    ]

    assert isinstance(call_tree.children[0], SfgSequence)
    for line, stmt in zip(lines, call_tree.children[0].children, strict=True):
        assert isinstance(stmt, SfgStatements)
        assert stmt.code_string == line


def test_duplicate_field_shapes(sfg):
    N, tx, ty = [TypedSymbol(n, create_type("int64")) for n in ("N", "tx", "ty")]
    f = Field("f", FieldType.GENERIC, "double", (1, 0), (N, N), (tx, ty))
    g = Field("g", FieldType.GENERIC, "double", (1, 0), (N, N), (tx, ty))

    @kernel
    def set_constant():
        f.center @= g.center(0)

    khandle = sfg.kernels.create(set_constant)

    call_tree = make_sequence(
        sfg.map_field(g, DemoFieldExtraction("g"), cast_indexing_symbols=False),
        sfg.map_field(f, DemoFieldExtraction("f"), cast_indexing_symbols=False),
        sfg.call(khandle),
    )

    pp = CallTreePostProcessing()
    _ = pp.get_live_variables(call_tree)

    lines_g = [
        r"double * RESTRICT const _data_g { g.ptr() };",
        r"/* g.size(0) == N */",
        r"/* g.size(1) == N */",
        r"/* g.stride(0) == tx */",
        r"/* g.stride(1) == ty */",
    ]

    assert isinstance(call_tree.children[0], SfgSequence)
    for line, stmt in zip(lines_g, call_tree.children[0].children, strict=True):
        assert isinstance(stmt, SfgStatements)
        assert stmt.code_string == line

    lines_f = [
        r"double * RESTRICT const _data_f { f.ptr() };",
        r"const int64_t N { f.size(0) };",
        r"/* f.size(1) == N */",
        r"const int64_t tx { f.stride(0) };",
        r"const int64_t ty { f.stride(1) };",
    ]

    assert isinstance(call_tree.children[1], SfgSequence)
    for line, stmt in zip(lines_f, call_tree.children[1].children, strict=True):
        assert isinstance(stmt, SfgStatements)
        assert stmt.code_string == line


def test_scalar_fields(sfg):
    sc_expl = Field.create_generic("f", 1, "double", index_shape=(1,))
    sc_impl = Field.create_generic("f", 1, "double", index_shape=())

    asm_expl = Assignment(sc_expl.center(0), 3)
    asm_impl = Assignment(sc_impl.center(), 3)

    k_expl = sfg.kernels.create(asm_expl, "expl")
    k_impl = sfg.kernels.create(asm_impl, "impl")

    tree_expl = make_sequence(
        sfg.map_field(sc_expl, std.span.from_field(sc_expl)), sfg.call(k_expl)
    )

    tree_impl = make_sequence(
        sfg.map_field(sc_impl, std.span.from_field(sc_impl)), sfg.call(k_impl)
    )

    pp = CallTreePostProcessing()
    _ = pp.get_live_variables(tree_expl)
    _ = pp.get_live_variables(tree_impl)

    extraction_expl = tree_expl.children[0]
    assert isinstance(extraction_expl, SfgSequence)

    extraction_impl = tree_impl.children[0]
    assert isinstance(extraction_impl, SfgSequence)

    for node1, node2 in zip(
        extraction_expl.children, extraction_impl.children, strict=True
    ):
        assert isinstance(node1, SfgStatements)
        assert isinstance(node2, SfgStatements)
        assert node1.code_string == node2.code_string
