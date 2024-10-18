#pragma once

#include <cstdint>

#define RESTRICT __restrict__

class Point {
public:
  const int64_t & getX() const {
    return this->x;
  }
private:
  int64_t x;
  int64_t y;
  int64_t z;
};
