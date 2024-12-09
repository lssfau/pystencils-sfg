import pytest
from pystencilssfg import SourceFileGenerator
import pystencilssfg.extensions.sycl as sycl
import pystencils as ps
from pystencilssfg import SfgContext


def test_parallel_for_1_kernels():
    sfg = sycl.SyclComposer(SfgContext())
    data_type = "double"
    dim = 2
    f, g, h, i = ps.fields(f"f,g,h,i:{data_type}[{dim}D]")
    assignement_1 = ps.Assignment(f.center(), g.center())
    assignement_2 = ps.Assignment(h.center(), i.center())

    config = ps.CreateKernelConfig(target=ps.Target.SYCL)
    kernel_1 = sfg.kernels.create(assignement_1, "kernel_1", config)
    kernel_2 = sfg.kernels.create(assignement_2, "kernel_2", config)
    cgh = sfg.sycl_handler("handler")
    rang = sfg.sycl_range(dim, "range")
    cgh.parallel_for(rang)(
        sfg.call(kernel_1),
        sfg.call(kernel_2),
    )


def test_parallel_for_2_kernels():
    sfg = sycl.SyclComposer(SfgContext())
    data_type = "double"
    dim = 2
    f, g, h, i = ps.fields(f"f,g,h,i:{data_type}[{dim}D]")
    assignement_1 = ps.Assignment(f.center(), g.center())
    assignement_2 = ps.Assignment(h.center(), i.center())

    config = ps.CreateKernelConfig(target=ps.Target.SYCL)
    kernel_1 = sfg.kernels.create(assignement_1, "kernel_1", config)
    kernel_2 = sfg.kernels.create(assignement_2, "kernel_2", config)
    cgh = sfg.sycl_handler("handler")
    rang = sfg.sycl_range(dim, "range")
    cgh.parallel_for(rang)(
        sfg.call(kernel_1),
        sfg.call(kernel_2),
    )


def test_parallel_for_2_kernels_fail():
    sfg = sycl.SyclComposer(SfgContext())
    data_type = "double"
    dim = 2
    f, g = ps.fields(f"f,g:{data_type}[{dim}D]")
    h, i = ps.fields(f"h,i:{data_type}[{dim-1}D]")
    assignement_1 = ps.Assignment(f.center(), g.center())
    assignement_2 = ps.Assignment(h.center(), i.center())

    config = ps.CreateKernelConfig(target=ps.Target.SYCL)
    kernel_1 = sfg.kernels.create(assignement_1, "kernel_1", config)
    kernel_2 = sfg.kernels.create(assignement_2, "kernel_2", config)
    cgh = sfg.sycl_handler("handler")
    rang = sfg.sycl_range(dim, "range")
    with pytest.raises(ValueError):
        cgh.parallel_for(rang)(
            sfg.call(kernel_1),
            sfg.call(kernel_2),
        )
