#include <iostream>
#include <fstream>

#include <cstdint>
#include <vector>

#include <experimental/mdspan>

#include "generated_src/kernels.h"

using field_t = std::mdspan< double, std::extents< uint32_t, std::dynamic_extent, std::dynamic_extent > >;

double boundary(double x, double y){
    return 1.0;
}

int main(int argc, char ** argv){
    uint32_t N = 8; /* number of grid nodes */
    double h = 1.0 / (double(N) - 1);
    uint32_t n_iters = 100;

    std::vector< double > data_src(N*N);
    field_t src(data_src.data(), N, N);

    std::vector< double > data_dst(N*N);
    field_t dst(data_dst.data(), N, N);

    std::vector< double > data_f(N*N);
    field_t f(data_f.data(), N, N);

    for(uint32_t i = 0; i < N; ++i){
        for(uint32_t j = 0; j < N; ++j){
            if(i == 0 || j == 0 || i == N-1 || j == N-1){
                src[i, j] = boundary(double(i) * h, double(j) * h);
                dst[i, j] = boundary(double(i) * h, double(j) * h);
                f[i, j] = 0.0;
            }
        }
    }
    
    for(uint32_t i = 0; i < n_iters; ++i){
        make_demo::jacobi::jacobi_smooth(f, h, dst, src);
        std::swap(src, dst);
    }

    std::ofstream file("data.out", std::ios::trunc | std::ios::out);

    if(!file.is_open()){
        std::cerr << "Could not open output file.\n";
    } else {
        for(uint32_t i = 0; i < N; ++i){
            for(uint32_t j = 0; j < N; ++j){
                file << src[i, j] << " ";
            }
            file << '\n';
        }
    }

    file.close();

    return 0;
}
