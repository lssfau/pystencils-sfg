import pytest


from pystencilssfg.lang.cpp import sycl
import pystencils as ps


@pytest.mark.parametrize("data_type", ["double", "float"])
@pytest.mark.parametrize("dim", [1, 2, 3])
def test_spatial_field(data_type, dim):
    f = ps.fields(f"f:{data_type}[{dim}D]")
    ref = sycl.accessor.from_field(f)
    assert f"sycl::accessor< {data_type}, {dim} >&" in str(ref.get_dtype())


@pytest.mark.parametrize("data_type", ["double", "float"])
def test_too_large_dim(data_type):
    dim = 4
    f = ps.fields(f"f:{data_type}[{dim}D]")
    with pytest.raises(ValueError):
        sycl.accessor.from_field(f)


@pytest.mark.parametrize("data_type", ["double", "float"])
@pytest.mark.parametrize("spatial_dim", [1, 2, 3])
@pytest.mark.parametrize("index_dims", [1, 2, 3])
def test_index_field(data_type, spatial_dim, index_dims):
    index_shape = ("19",) * index_dims
    total_dims = spatial_dim + index_dims
    f = ps.fields(f"f({', '.join(index_shape)}):{data_type}[{spatial_dim}D]")
    if total_dims <= 3:
        ref = sycl.accessor.from_field(f)
        assert f"sycl::accessor< {data_type}, {total_dims} >&" in str(ref.get_dtype())
    else:
        with pytest.raises(ValueError):
            sycl.accessor.from_field(f)
