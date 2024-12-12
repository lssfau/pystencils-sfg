#include "StlContainers1D.hpp"

#include <iostream>
#include <span>
#include <vector>
#include <random>
#include <cmath>
#include <memory>

#ifdef NDEBUG
#undef NDEBUG
#include <cassert>
#define NDEBUG
#else
#include <cassert>
#endif

namespace StlContainers1D
{
    constexpr size_t N{974};
    constexpr double one_third { 1.0 / 3.0 };

    void test_vector_kernel()
    {
        std::random_device rd;
        std::mt19937 gen{ rd() };
        std::uniform_real_distribution<double> distrib{-1.0, 1.0};

        std::vector<double> src;
        std::vector<double> dst;

        src.resize(N);
        dst.resize(N);

        for (size_t i = 0; i < N; ++i)
        {
            src[i] = distrib(gen);
            dst[i] = 0.0;
        }

        gen::averageVector(dst, src);

        for (size_t i = 1; i < N - 1; ++i)
        {
            const double desired = one_third * ( src[i - 1] + src[i] + src[i + 1] );
            assert( std::abs(desired - dst[i]) < 1e-12 );
        }
    }

    void test_span_kernel()
    {
        std::random_device rd;
        std::mt19937 gen{ rd() };
        std::uniform_real_distribution<double> distrib{-1.0, 1.0};

        auto src_data = std::make_unique< double[] >(N);
        auto dst_data = std::make_unique< double[] >(N);

        std::span< double > src{ src_data.get(), N };
        std::span< double > dst{ dst_data.get(), N };

        for (size_t i = 0; i < N; ++i)
        {
            src[i] = distrib(gen);
            dst[i] = 0.0;
        }

        gen::averageSpan(dst, src);

        for (size_t i = 1; i < N - 1; ++i)
        {
            const double desired = one_third * ( src[i - 1] + src[i] + src[i + 1] );
            assert( std::abs(desired - dst[i]) < 1e-12 );
        }
    }

}


int main(void)
{
    StlContainers1D::test_vector_kernel();
    StlContainers1D::test_span_kernel();
    return 0;
}
