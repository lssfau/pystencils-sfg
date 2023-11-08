#include "TestSequencing.h"

#define FUNC_PREFIX inline

namespace pystencils {

/*************************************************************************************
 *                                Kernels
*************************************************************************************/

namespace kernels{


FUNC_PREFIX void streamCollide_even( double * RESTRICT const _data_src, int64_t const _size_src_0, int64_t const _size_src_1, int64_t const _stride_src_0, int64_t const _stride_src_1, int64_t const _stride_src_2, double omega)
{
   for (int64_t ctr_1 = 1; ctr_1 < _size_src_1 - 1; ctr_1 += 1)
   {
      for (int64_t ctr_0 = 1; ctr_0 < _size_src_0 - 1; ctr_0 += 1)
      {
         const double xi_1 = _data_src[_stride_src_0*ctr_0 + _stride_src_0 + _stride_src_1*ctr_1 + _stride_src_1 + 7*_stride_src_2];
         const double xi_2 = _data_src[_stride_src_0*ctr_0 + _stride_src_0 + _stride_src_1*ctr_1 + 5*_stride_src_2];
         const double xi_3 = _data_src[_stride_src_0*ctr_0 + _stride_src_1*ctr_1];
         const double xi_4 = _data_src[_stride_src_0*ctr_0 + _stride_src_1*ctr_1 + 4*_stride_src_2];
         const double xi_5 = _data_src[_stride_src_0*ctr_0 + _stride_src_1*ctr_1 + 6*_stride_src_2];
         const double xi_6 = _data_src[_stride_src_0*ctr_0 + _stride_src_1*ctr_1 + _stride_src_1 + 2*_stride_src_2];
         const double xi_7 = _data_src[_stride_src_0*ctr_0 + _stride_src_0 + _stride_src_1*ctr_1 + 3*_stride_src_2];
         const double xi_8 = _data_src[_stride_src_0*ctr_0 + _stride_src_1*ctr_1 + _stride_src_1 + 8*_stride_src_2];
         const double xi_9 = _data_src[_stride_src_0*ctr_0 + _stride_src_1*ctr_1 + _stride_src_2];
         const double vel0Term = xi_4 + xi_5 + xi_8;
         const double vel1Term = xi_2 + xi_9;
         const double delta_rho = vel0Term + vel1Term + xi_1 + xi_3 + xi_6 + xi_7;
         const double u_0 = vel0Term - xi_1 - xi_2 - xi_7;
         const double u_1 = vel1Term - xi_1 + xi_5 - xi_6 - xi_8;
         const double u0Mu1 = u_0 - u_1;
         const double u0Pu1 = u_0 + u_1;
         const double f_eq_common = delta_rho - 1.5*(u_0*u_0) - 1.5*(u_1*u_1);
         _data_src[_stride_src_0*ctr_0 + _stride_src_1*ctr_1] = omega*(f_eq_common*0.44444444444444442 - xi_3) + xi_3;
         _data_src[_stride_src_0*ctr_0 + _stride_src_1*ctr_1 + _stride_src_1 + 2*_stride_src_2] = omega*(f_eq_common*0.1111111111111111 + u_1*0.33333333333333331 - xi_9 + 0.5*(u_1*u_1)) + xi_9;
         _data_src[_stride_src_0*ctr_0 + _stride_src_1*ctr_1 + _stride_src_2] = omega*(f_eq_common*0.1111111111111111 + u_1*-0.33333333333333331 - xi_6 + 0.5*(u_1*u_1)) + xi_6;
         _data_src[_stride_src_0*ctr_0 + _stride_src_1*ctr_1 + 4*_stride_src_2] = omega*(f_eq_common*0.1111111111111111 + u_0*-0.33333333333333331 - xi_7 + 0.5*(u_0*u_0)) + xi_7;
         _data_src[_stride_src_0*ctr_0 + _stride_src_0 + _stride_src_1*ctr_1 + 3*_stride_src_2] = omega*(f_eq_common*0.1111111111111111 + u_0*0.33333333333333331 - xi_4 + 0.5*(u_0*u_0)) + xi_4;
         _data_src[_stride_src_0*ctr_0 + _stride_src_1*ctr_1 + _stride_src_1 + 8*_stride_src_2] = omega*(f_eq_common*0.027777777777777776 + u0Mu1*-0.083333333333333329 - xi_2 + 0.125*(u0Mu1*u0Mu1)) + xi_2;
         _data_src[_stride_src_0*ctr_0 + _stride_src_0 + _stride_src_1*ctr_1 + _stride_src_1 + 7*_stride_src_2] = omega*(f_eq_common*0.027777777777777776 + u0Pu1*0.083333333333333329 - xi_5 + 0.125*(u0Pu1*u0Pu1)) + xi_5;
         _data_src[_stride_src_0*ctr_0 + _stride_src_1*ctr_1 + 6*_stride_src_2] = omega*(f_eq_common*0.027777777777777776 + u0Pu1*-0.083333333333333329 - xi_1 + 0.125*(u0Pu1*u0Pu1)) + xi_1;
         _data_src[_stride_src_0*ctr_0 + _stride_src_0 + _stride_src_1*ctr_1 + 5*_stride_src_2] = omega*(f_eq_common*0.027777777777777776 + u0Mu1*0.083333333333333329 - xi_8 + 0.125*(u0Mu1*u0Mu1)) + xi_8;
      }
   }
}

FUNC_PREFIX void streamCollide_odd( double * RESTRICT const _data_src, int64_t const _size_src_0, int64_t const _size_src_1, int64_t const _stride_src_0, int64_t const _stride_src_1, int64_t const _stride_src_2, double omega)
{
   for (int64_t ctr_1 = 1; ctr_1 < _size_src_1 - 1; ctr_1 += 1)
   {
      for (int64_t ctr_0 = 1; ctr_0 < _size_src_0 - 1; ctr_0 += 1)
      {
         const double xi_1 = _data_src[_stride_src_0*ctr_0 + _stride_src_1*ctr_1 + _stride_src_1 + 5*_stride_src_2];
         const double xi_2 = _data_src[_stride_src_0*ctr_0 + _stride_src_1*ctr_1];
         const double xi_3 = _data_src[_stride_src_0*ctr_0 + _stride_src_0 + _stride_src_1*ctr_1 + _stride_src_1 + 6*_stride_src_2];
         const double xi_4 = _data_src[_stride_src_0*ctr_0 + _stride_src_1*ctr_1 + 2*_stride_src_2];
         const double xi_5 = _data_src[_stride_src_0*ctr_0 + _stride_src_1*ctr_1 + 3*_stride_src_2];
         const double xi_6 = _data_src[_stride_src_0*ctr_0 + _stride_src_0 + _stride_src_1*ctr_1 + 8*_stride_src_2];
         const double xi_7 = _data_src[_stride_src_0*ctr_0 + _stride_src_1*ctr_1 + 7*_stride_src_2];
         const double xi_8 = _data_src[_stride_src_0*ctr_0 + _stride_src_1*ctr_1 + _stride_src_1 + _stride_src_2];
         const double xi_9 = _data_src[_stride_src_0*ctr_0 + _stride_src_0 + _stride_src_1*ctr_1 + 4*_stride_src_2];
         const double vel0Term = xi_1 + xi_5 + xi_7;
         const double vel1Term = xi_4 + xi_6;
         const double delta_rho = vel0Term + vel1Term + xi_2 + xi_3 + xi_8 + xi_9;
         const double u_0 = vel0Term - xi_3 - xi_6 - xi_9;
         const double u_1 = vel1Term - xi_1 - xi_3 + xi_7 - xi_8;
         const double u0Mu1 = u_0 - u_1;
         const double u0Pu1 = u_0 + u_1;
         const double f_eq_common = delta_rho - 1.5*(u_0*u_0) - 1.5*(u_1*u_1);
         _data_src[_stride_src_0*ctr_0 + _stride_src_1*ctr_1] = omega*(f_eq_common*0.44444444444444442 - xi_2) + xi_2;
         _data_src[_stride_src_0*ctr_0 + _stride_src_1*ctr_1 + _stride_src_1 + _stride_src_2] = omega*(f_eq_common*0.1111111111111111 + u_1*0.33333333333333331 - xi_4 + 0.5*(u_1*u_1)) + xi_4;
         _data_src[_stride_src_0*ctr_0 + _stride_src_1*ctr_1 + 2*_stride_src_2] = omega*(f_eq_common*0.1111111111111111 + u_1*-0.33333333333333331 - xi_8 + 0.5*(u_1*u_1)) + xi_8;
         _data_src[_stride_src_0*ctr_0 + _stride_src_1*ctr_1 + 3*_stride_src_2] = omega*(f_eq_common*0.1111111111111111 + u_0*-0.33333333333333331 - xi_9 + 0.5*(u_0*u_0)) + xi_9;
         _data_src[_stride_src_0*ctr_0 + _stride_src_0 + _stride_src_1*ctr_1 + 4*_stride_src_2] = omega*(f_eq_common*0.1111111111111111 + u_0*0.33333333333333331 - xi_5 + 0.5*(u_0*u_0)) + xi_5;
         _data_src[_stride_src_0*ctr_0 + _stride_src_1*ctr_1 + _stride_src_1 + 5*_stride_src_2] = omega*(f_eq_common*0.027777777777777776 + u0Mu1*-0.083333333333333329 - xi_6 + 0.125*(u0Mu1*u0Mu1)) + xi_6;
         _data_src[_stride_src_0*ctr_0 + _stride_src_0 + _stride_src_1*ctr_1 + _stride_src_1 + 6*_stride_src_2] = omega*(f_eq_common*0.027777777777777776 + u0Pu1*0.083333333333333329 - xi_7 + 0.125*(u0Pu1*u0Pu1)) + xi_7;
         _data_src[_stride_src_0*ctr_0 + _stride_src_1*ctr_1 + 7*_stride_src_2] = omega*(f_eq_common*0.027777777777777776 + u0Pu1*-0.083333333333333329 - xi_3 + 0.125*(u0Pu1*u0Pu1)) + xi_3;
         _data_src[_stride_src_0*ctr_0 + _stride_src_0 + _stride_src_1*ctr_1 + 8*_stride_src_2] = omega*(f_eq_common*0.027777777777777776 + u0Mu1*0.083333333333333329 - xi_1 + 0.125*(u0Mu1*u0Mu1)) + xi_1;
      }
   }
}


} // namespace kernels


/*************************************************************************************
 *                                Functions
*************************************************************************************/



void myFunction (  double * RESTRICT const _data_src, int64_t const _size_src_0, int64_t const _size_src_1, int64_t const _stride_src_0, int64_t const _stride_src_1, int64_t const _stride_src_2, double omega ) { 
  if((timestep & 1) ^ 1) {
    pystencils::kernels::streamCollide_even(_data_src, _size_src_0, _size_src_1, _stride_src_0, _stride_src_1, _stride_src_2, omega);
  }else {
    pystencils::kernels::streamCollide_odd(_data_src, _size_src_0, _size_src_1, _stride_src_0, _stride_src_1, _stride_src_2, omega);
  }
}



} // namespace pystencils