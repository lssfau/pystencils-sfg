#include "HipKernels.hpp"

#include <hip/hip_runtime.h>

#include <experimental/mdspan>
#include <random>
#include <iostream>
#include <functional>

#undef NDEBUG
#include <cassert>

namespace stdex = std::experimental;

using extents_t = stdex::dextents<uint64_t, 3>;
using field_t = stdex::mdspan<double, extents_t, stdex::layout_right>;

void checkHipError(hipError_t err)
{
    if (err != hipSuccess)
    {
        std::cerr << "HIP Error: " << err << std::endl;
        exit(2);
    }
}

int main(void)
{

    extents_t extents{23, 25, 132};
    size_t items{extents.extent(0) * extents.extent(1) * extents.extent(2)};

    double *data_src;
    checkHipError(hipMallocManaged<double>(&data_src, sizeof(double) * items));
    field_t src{data_src, extents};

    double *data_dst;
    checkHipError(hipMallocManaged<double>(&data_dst, sizeof(double) * items));
    field_t dst{data_dst, extents};

    std::random_device rd;
    std::mt19937 gen{rd()};
    std::uniform_real_distribution<double> distrib{-1.0, 1.0};

    auto check = [&](std::function<void()> invoke)
    {
        for (size_t i = 0; i < items; ++i)
        {
            data_src[i] = distrib(gen);
            data_dst[i] = NAN;
        }

        invoke();

        for (size_t i = 0; i < items; ++i)
        {
            const double desired = 2.0 * data_src[i];
            if (std::abs(desired - data_dst[i]) >= 1e-12)
            {
                std::cerr << "Mismatch at element " << i << "; Desired: " << desired << "; Actual: " << data_dst[i] << std::endl;
                exit(EXIT_FAILURE);
            }
        }
    };

    check([&]()
          {
        /* Linear3D Dynamic */
        dim3 blockSize{64, 8, 1};
        hipStream_t stream;
        checkHipError(hipStreamCreate(&stream));
        gen::linear3d::scaleKernel(blockSize, dst, src, stream);
        checkHipError(hipStreamSynchronize(stream)); });

    check([&]()
          {
        /* Linear3D Automatic */
        hipStream_t stream;
        checkHipError(hipStreamCreate(&stream));
        gen::linear3d_automatic::scaleKernel(dst, src, stream);
        checkHipError(hipStreamSynchronize(stream)); });

    check([&]()
          {
        /* Blockwise4D Automatic */
        hipStream_t stream;
        checkHipError(hipStreamCreate(&stream));
        gen::blockwise4d::scaleKernel(dst, src, stream);
        checkHipError(hipStreamSynchronize(stream)); });

    check([&]()
          {
        /* Linear3D Manual */
        dim3 blockSize{32, 8, 1};
        dim3 gridSize{5, 4, 23};

        hipStream_t stream;
        checkHipError(hipStreamCreate(&stream));
        gen::linear3d_manual::scaleKernel(blockSize, dst, gridSize, src, stream);
        checkHipError(hipStreamSynchronize(stream)); });

    check([&]()
          {
        /* Blockwise4D Manual */
        dim3 blockSize{132, 1, 1};
        dim3 gridSize{25, 23, 1};
        hipStream_t stream;
        checkHipError(hipStreamCreate(&stream));
        gen::blockwise4d_manual::scaleKernel(blockSize, dst, gridSize, src, stream);
        checkHipError(hipStreamSynchronize(stream)); });

    checkHipError(hipFree(data_src));
    checkHipError(hipFree(data_dst));

    return EXIT_SUCCESS;
}
