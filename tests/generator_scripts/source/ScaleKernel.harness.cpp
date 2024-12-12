#include "ScaleKernel.hpp"

#include <vector>

#define NDEBUG
#include <cassert>

int main(void){
    std::vector< float > src;
    src.resize(gen::N);

    std::vector< float > dst;
    dst.resize(gen::N);

    for(int i = 0; i < gen::N; ++i){
        src[i] = 1.0f;
    }

    float alpha = 2.5f;

    gen::Scale scale{ alpha };
    scale(dst.data(), src.data());
    
    for(int i = 0; i < gen::N; ++i){
        assert( dst[i] == alpha );
    }
}
