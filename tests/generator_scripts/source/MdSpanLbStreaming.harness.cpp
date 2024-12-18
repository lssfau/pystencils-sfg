#include "MdSpanLbStreaming.hpp"

#include <concepts>
#include <experimental/mdspan>
#include <array>
#include <cassert>
#include <memory>
#include <span>

namespace stdex = std::experimental;

static_assert(std::is_same_v<gen::field_fzyx::layout_type, stdex::layout_left>);
static_assert(std::is_same_v<gen::field_zyxf::layout_type, stdex::layout_stride>);
static_assert(std::is_same_v<gen::field_c::layout_type, stdex::layout_right>);

using shape_type = stdex::extents< int64_t, std::dynamic_extent, std::dynamic_extent, std::dynamic_extent, 6 >;
static_assert(std::is_same_v<gen::field_fzyx::extents_type, shape_type >);

constexpr shape_type field_shape { 16l, 15l, 14l };

constexpr std::array<std::array<int64_t, 3>, 2> slice{
    {{3, 4, 5},
     {7, 10, 12}}};

template <typename Kernel, typename PdfField>
void test_streaming(Kernel &kernel, PdfField &src_field, PdfField &dst_field)
{
    kernel.setZero(src_field);
    kernel.setZero(dst_field);

    for (int64_t z = slice[0][2]; z < slice[1][2]; ++z)
        for (int64_t y = slice[0][1]; y < slice[1][1]; ++y)
            for (int64_t x = slice[0][0]; x < slice[1][0]; ++x)
                for (int64_t i = 0; i < int64_t(gen::STENCIL.size()); ++i)
                {
                    src_field(x, y, z, i) = double(i);
                }

    kernel(dst_field, src_field);

    for (int64_t z = slice[0][2]; z < slice[1][2]; ++z)
        for (int64_t y = slice[0][1]; y < slice[1][1]; ++y)
            for (int64_t x = slice[0][0]; x < slice[1][0]; ++x)
                for (int64_t i = 0; i < int64_t(gen::STENCIL.size()); ++i)
                {
                    const std::array<int64_t, 3> &offsets = gen::STENCIL[i];
                    assert((dst_field(x + offsets[0], y + offsets[1], z + offsets[2], i) == double(i)));
                }
}

int main(void)
{
    constexpr size_t num_items { (size_t) field_shape.extent(0) * field_shape.extent(1) * field_shape.extent(2) * field_shape.extent(3) };

    auto src_data = std::make_unique< double [] >( num_items );
    auto dst_data = std::make_unique< double [] >( num_items );

    // Structure-of-Arrays
    {
        gen::Kernel_fzyx kernel;
        gen::field_fzyx src_arr { src_data.get(), field_shape };
        gen::field_fzyx dst_arr { dst_data.get(), field_shape };
        test_streaming(kernel, src_arr, dst_arr );
    }

    // Array-of-Structures
    {
        gen::Kernel_zyxf kernel;
        
        std::array< uint64_t, 4 > strides_xyzf {
            /* stride(x) */ field_shape.extent(3),
            /* stride(y) */ field_shape.extent(3) * field_shape.extent(0),
            /* stride(z) */ field_shape.extent(3) * field_shape.extent(0) * field_shape.extent(1),
            /* stride(f) */ 1
        };

        gen::field_zyxf::mapping_type zyxf_mapping { field_shape, strides_xyzf };  

        gen::field_zyxf src_arr { src_data.get(), zyxf_mapping };
        gen::field_zyxf dst_arr { dst_data.get(), zyxf_mapping };
        test_streaming(kernel, src_arr, dst_arr );
    }

    // C Row-Major
    {
        gen::Kernel_c kernel;
        gen::field_c src_arr { src_data.get(), field_shape };
        gen::field_c dst_arr { dst_data.get(), field_shape };
        test_streaming(kernel, src_arr, dst_arr );
    }
}
