import sympy as sp
from pystencils import fields, kernel, TypedSymbol

from pystencilssfg import SfgContext, SfgComposer
from pystencilssfg.composer import make_sequence

from pystencilssfg.ir import SfgStatements
from pystencilssfg.ir.postprocessing import CallTreePostProcessing


def test_live_vars():
    ctx = SfgContext()
    sfg = SfgComposer(ctx)

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


def test_find_sympy_symbols():
    ctx = SfgContext()
    sfg = SfgComposer(ctx)

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
