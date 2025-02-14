from pystencilssfg.extensions.gpu import dim3class
from pystencilssfg.lang import HeaderFile, AugExpr


def test_dim3():
    cuda_runtime = "<cuda_runtime.h>"
    dim3 = dim3class(cuda_runtime, cls_name="dim3")
    assert HeaderFile.parse(cuda_runtime) in dim3.template.includes
    assert str(dim3().ctor(128, 1, 1)) == "dim3{128, 1, 1}"
    assert str(dim3().ctor()) == "dim3{1, 1, 1}"
    assert str(dim3().ctor(1, 1, 128)) == "dim3{1, 1, 128}"

    block = dim3(ref=True, const=True).var("block")

    dims = [
        AugExpr.format(
            "uint32_t(({} + {} - 1)/ {})",
            1024,
            block.dims[i],
            block.dims[i],
        )
        for i in range(3)
    ]

    grid = dim3().ctor(*dims)
    assert str(grid) == f"dim3{{{', '.join((str(d) for d in dims))}}}"
