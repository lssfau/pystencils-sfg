#include "SimpleClasses.hpp"

#define NDEBUG
#include <cassert>

int main(void){
    Point p { 3, 1, -4 };

    assert(p.getX() == 3);

    SpecialPoint q { 0, 1, 2 };
    assert(q.getY() == 1);
}
