#include "NestedNamespaces.hpp"

static_assert( outer::X == 13 );
static_assert( outer::inner::Y == 52 );
static_assert( outer::Z == 41 );
static_assert( outer::second_inner::W == 91 );
static_assert( outer::inner::innermost::V == 29 );
static_assert( GLOBAL == 42 );

int main() {
    return 0;
}
