#include "ComposerFeatures.hpp"

#include <cmath>

#undef NDEBUG
#include <cassert>

/* Evaluate constexpr functions at compile-time */
static_assert( factorial(0) == 1 );
static_assert( factorial(1) == 1 );
static_assert( factorial(2) == 2 );
static_assert( factorial(3) == 6 );
static_assert( factorial(4) == 24 );
static_assert( factorial(5) == 120 );

static_assert( ConstexprMath::abs(ConstexprMath::geometric(0.5, 0) - 1.0) < 1e-10 );
static_assert( ConstexprMath::abs(ConstexprMath::geometric(0.5, 1) - 1.5) < 1e-10 );
static_assert( ConstexprMath::abs(ConstexprMath::geometric(0.5, 2) - 1.75) < 1e-10 );
static_assert( ConstexprMath::abs(ConstexprMath::geometric(0.5, 3) - 1.875) < 1e-10 );

int main(void) {
    assert( std::fabs(Series::geometric(0.5, 0) - 1.0) < 1e-10 );
    assert( std::fabs(Series::geometric(0.5, 1) - 1.5) < 1e-10 );
    assert( std::fabs(Series::geometric(0.5, 2) - 1.75) < 1e-10 );
    assert( std::fabs(Series::geometric(0.5, 3) - 1.875) < 1e-10 );

    inheritance_test::Parent p;
    assert( p.compute() == 24 );

    inheritance_test::Child c;
    assert( c.compute() == 31 );

    auto & cp = dynamic_cast< inheritance_test::Parent & >(c);
    assert( cp.compute() == 31 );
}
