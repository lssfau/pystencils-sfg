#include "VectorExtraction.hpp"
#include <experimental/mdspan>
#include <memory>
#include <vector>

#undef NDEBUG
#include <cassert>

namespace stdex = std::experimental;

using extents_t = stdex::extents<std::int64_t, std::dynamic_extent, std::dynamic_extent, 3>;
using vector_field_t = stdex::mdspan<double, extents_t, stdex::layout_right>;
constexpr size_t N{41};

int main(void)
{
    auto u_data = std::make_unique<double[]>(N * N * 3);
    vector_field_t u_field{u_data.get(), extents_t{N, N}};
    std::vector<double> v{3.1, 3.2, 3.4};

    gen::invoke(u_field, v);

    for (size_t j = 0; j < N; ++j)
        for (size_t i = 0; i < N; ++i)
        {
            assert(u_field(j, i, 0) == v[0]);
            assert(u_field(j, i, 1) == v[1]);
            assert(u_field(j, i, 2) == v[2]);
        }
}