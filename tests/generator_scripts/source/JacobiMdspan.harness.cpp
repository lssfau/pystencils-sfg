#include "JacobiMdspan.hpp"

#include <experimental/mdspan>
#include <memory>

namespace stdex = std::experimental;

using field_t = stdex::mdspan<double, stdex::extents<int64_t, std::dynamic_extent, std::dynamic_extent>, stdex::layout_left>;
using scalar_field_t = stdex::mdspan<double, stdex::extents<int64_t, std::dynamic_extent, std::dynamic_extent, 1>, stdex::layout_left>;

int main(void)
{
    auto data_f = std::make_unique<double[]>(64);
    scalar_field_t f{data_f.get(), 8, 8};

    auto data_u = std::make_unique<double[]>(64);
    field_t u{data_u.get(), 8, 8};

    auto data_u_tmp = std::make_unique<double[]>(64);
    field_t u_tmp{data_u_tmp.get(), 8, 8};

    double h{1.0 / 7.0};

    gen::jacobi_smooth(f, h, u_tmp, u);
}
