#include <sycl/sycl.hpp>
#include <iostream>

#include "SyclBuffers.hpp"

int main(void) {
    sycl::queue queue;
    {
        sycl::range< 2 > domainSize { 64, 64 };
        const double h { 1.0 / 63.0 };
        sycl::buffer< double, 2 > u { domainSize };
        sycl::buffer< double, 2 > uTmp { domainSize };
        sycl::buffer< double, 2 > f { domainSize };

        queue.submit([&](sycl::handler & cgh){
            sycl::accessor uAcc { u, cgh };
            sycl::accessor uTmpAcc { uTmp, cgh };
            sycl::accessor fAcc { f, cgh };

            gen::jacobiUpdate(fAcc, h, cgh, domainSize, uTmpAcc, uAcc);
        });
    }
}
