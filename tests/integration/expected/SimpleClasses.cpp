#include <cstdint>

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
