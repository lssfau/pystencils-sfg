#include "MdSpanLayouts.hpp"

#include <concepts>
#include <experimental/mdspan>

namespace stdex = std::experimental;

static_assert( std::is_same_v< gen::field_soa::layout_type, stdex::layout_left > );
static_assert( std::is_same_v< gen::field_aos::layout_type, stdex::layout_stride > );
static_assert( std::is_same_v< gen::field_c::layout_type, stdex::layout_right > );

static_assert( gen::field_soa::static_extent(0) == 17 );
static_assert( gen::field_soa::static_extent(1) == 19 );
static_assert( gen::field_soa::static_extent(2) == 32 );
static_assert( gen::field_soa::static_extent(3) == 9 );

int main(void) {
    gen::field_soa f_soa { nullptr };
    gen::checkLayoutSoa(f_soa);

    gen::field_aos::extents_type f_aos_extents { };
    std::array< uint64_t, 4 > strides_aos {
        /* stride(x) */ f_aos_extents.extent(3),
        /* stride(y) */ f_aos_extents.extent(3) * f_aos_extents.extent(0),
        /* stride(z) */ f_aos_extents.extent(3) * f_aos_extents.extent(0) * f_aos_extents.extent(1),
        /* stride(f) */ 1
    };

    gen::field_aos::mapping_type f_aos_mapping { f_aos_extents, strides_aos };
    gen::field_aos f_aos { nullptr, f_aos_mapping };
    gen::checkLayoutAos(f_aos);

    gen::field_c f_c { nullptr };
    gen::checkLayoutC(f_c);
}
