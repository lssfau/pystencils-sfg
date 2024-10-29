#pragma once

#include <cstdint>

#define RESTRICT __restrict__

class Scale {
private:
    float alpha;
public:
    Scale(float alpha) : alpha{ alpha } {}
    void operator() (float *RESTRICT const _data_f, float *RESTRICT const _data_g);
};
