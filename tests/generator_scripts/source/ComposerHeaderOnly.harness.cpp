#include "ComposerHeaderOnly.hpp"

#include <vector>

#undef NDEBUG
#include <cassert>

int main(void) {
    assert( twice(13) == 26 );

    {
        std::vector< int64_t > arr { 1, 2, 3, 4, 5, 6 };
        twiceKernel(arr);

        std::vector< int64_t > expected { 2, 4, 6, 8, 10, 12 };
        assert ( arr == expected );
    }
    
    {
        std::vector< int64_t > arr { 1, 2, 3, 4, 5, 6 };
        ScaleKernel ker { 3 };

        ker( arr );

        std::vector< int64_t > expected { 3, 6, 9, 12, 15, 18 };
        assert ( arr == expected );
    }

    return 0;
}
