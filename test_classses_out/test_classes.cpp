

#include "test_classes.h"


#define FUNC_PREFIX inline


/*************************************************************************************
 *                                Kernels
*************************************************************************************/

namespace kernels {

FUNC_PREFIX void kernel(double * RESTRICT  _data_f, double * RESTRICT const _data_g, int64_t const _size_f_0, int64_t const _size_f_1, int64_t const _stride_f_0, int64_t const _stride_f_1, int64_t const _stride_g_0, int64_t const _stride_g_1)
{
   for (int64_t ctr_0 = 0; ctr_0 < _size_f_0; ctr_0 += 1)
   {
      for (int64_t ctr_1 = 0; ctr_1 < _size_f_1; ctr_1 += 1)
      {
         _data_f[_stride_f_0*ctr_0 + _stride_f_1*ctr_1] = 3.0*_data_g[_stride_g_0*ctr_0 + _stride_g_1*ctr_1];
      }
   }
}

} // namespace kernels

/*************************************************************************************
 *                                Functions
*************************************************************************************/


