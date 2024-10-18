# The pystencils Source File Generator

```{toctree}
:maxdepth: 1
:hidden:

usage/index
api/index
```

[![pipeline](https://i10git.cs.fau.de/pycodegen/pystencils-sfg/badges/master/pipeline.svg)](https://i10git.cs.fau.de/pycodegen-/pystencils-sfg/commits/master)
[![coverage](https://i10git.cs.fau.de/pycodegen/pystencils-sfg/badges/master/coverage.svg)](https://i10git.cs.fau.de/pycodegen-/pystencils-sfg/commits/master)
[![licence](https://img.shields.io/gitlab/license/pycodegen%2Fpystencils-sfg?gitlab_url=https%3A%2F%2Fi10git.cs.fau.de)](https://i10git.cs.fau.de/pycodegen/pystencils-sfg/-/blob/master/LICENSE)

A bridge over the semantic gap between code emitted by [pystencils](https://pypi.org/project/pystencils/)
and your C/C++/Cuda/HIP framework.

## Installation

### From Git

Install the package into your current Python environment from the git repository using pip
(usage of virtual environments is strongly encouraged!):

```bash
pip install "git+https://i10git.cs.fau.de/pycodegen/pystencils-sfg.git"
```

````{caution}

*pystencils-sfg* requires *pystencils 2.0* and is not compatible with *pystencils 1.3.x*.
However, *pystencils 2.0* is still under development and only available as a pre-release version.
To use *pystencils-sfg*, explicitly install *pystencils* from the v2.0 development branch:
   
```bash
pip install "git+https://i10git.cs.fau.de/pycodegen/pystencils.git@v2.0-dev"
```
````

### From PyPI

Not yet available.

## Primer

With *pystencils-sfg*, including your *pystencils*-generated kernels with handwritten code becomes straightforward
and intuitive. To illustrate, generating a Jacobi smoother for the two-dimensional Poisson equation
and mapping it onto C++23 `std::mdspan`s takes just a few lines of code:

```python
import sympy as sp

from pystencils import fields, kernel

from pystencilssfg import SourceFileGenerator
from pystencilssfg.lang.cpp import mdspan_ref

with SourceFileGenerator() as sfg:
    u_src, u_dst, f = fields("u_src, u_dst, f(1) : double[2D]", layout="fzyx")
    h = sp.Symbol("h")

    @kernel
    def poisson_jacobi():
        u_dst[0,0] @= (h**2 * f[0, 0] + u_src[1, 0] + u_src[-1, 0] + u_src[0, 1] + u_src[0, -1]) / 4

    poisson_kernel = sfg.kernels.create(poisson_jacobi)

    sfg.function("jacobi_smooth")(
        sfg.map_field(u_src, mdspan_ref(u_src)),
        sfg.map_field(u_dst, mdspan_ref(u_dst)),
        sfg.map_field(f, mdspan_ref(f)),
        sfg.call(poisson_kernel)
    )
```

The script above, and the code within the region controlled by the `SourceFileGenerator`,
constructs a C++ header/implementation file pair by describing its contents.
We first describe our Jacobi smoother symbolically using *pystencils*
and then pass it to the `sfg` to add it to the output file.
Then, a wrapper function `jacobi_smooth` is defined which maps the symbolic fields onto `std::mdspan`
objects and then executes the kernel.

Take this code, store it into a file `poisson_smoother.py`, and execute the script from a terminal:

```shell
python poisson_smoother.py
```

During execution, *pystencils-sfg* assembles the above constructs into an internal representation of the C++ files.
It then takes the name of your Python script, replaces `.py` with `.cpp` and `.h`,
and exports the constructed code to the files 
`poisson_smoother.cpp` and `poisson_smoother.h` into the current directory, ready to be `#include`d.

````{dropdown} poisson_smoother.h

```C++
#pragma once

#include <cstdint>
#include <experimental/mdspan>

#define RESTRICT __restrict__

void jacobi_smooth(
    std::mdspan<double, std::extents<uint64_t, std::dynamic_extent, std::dynamic_extent, 1>> &f,
    const double h,
    std::mdspan<double, std::extents<uint64_t, std::dynamic_extent, std::dynamic_extent>> &u_dst,
    std::mdspan<double, std::extents<uint64_t, std::dynamic_extent, std::dynamic_extent>> &u_src
);
```

````

````{dropdown} poisson_smoother.cpp

```C++
#include "poisson_smoother.h"

#include <math.h>

#define FUNC_PREFIX inline

/*************************************************************************************
 *                                Kernels
 *************************************************************************************/

namespace kernels {

FUNC_PREFIX void kernel(const int64_t _size_f_0, const int64_t _size_f_1,
                        const int64_t _stride_f_0, const int64_t _stride_f_1,
                        const int64_t _stride_u_dst_0,
                        const int64_t _stride_u_dst_1,
                        const int64_t _stride_u_src_0,
                        const int64_t _stride_u_src_1, double *const f_data,
                        const double h, double *const u_dst_data,
                        double *const u_src_data) {
  const double __c_1_0o4_0 = 1.0 / 4.0;
  for (int64_t ctr_1 = 1LL; ctr_1 < _size_f_1 - 1LL; ctr_1 += 1LL) {
    for (int64_t ctr_0 = 1LL; ctr_0 < _size_f_0 - 1LL; ctr_0 += 1LL) {
      u_dst_data[ctr_0 * _stride_u_dst_0 + ctr_1 * _stride_u_dst_1] =
          __c_1_0o4_0 * u_src_data[(ctr_0 + 1LL) * _stride_u_src_0 +
                                   ctr_1 * _stride_u_src_1] +
          __c_1_0o4_0 * u_src_data[ctr_0 * _stride_u_src_0 +
                                   (ctr_1 + 1LL) * _stride_u_src_1] +
          __c_1_0o4_0 * u_src_data[ctr_0 * _stride_u_src_0 +
                                   (ctr_1 + -1LL) * _stride_u_src_1] +
          __c_1_0o4_0 * u_src_data[(ctr_0 + -1LL) * _stride_u_src_0 +
                                   ctr_1 * _stride_u_src_1] +
          __c_1_0o4_0 * (h * h) *
              f_data[ctr_0 * _stride_f_0 + ctr_1 * _stride_f_1];
    }
  }
}

} // namespace kernels

/*************************************************************************************
 *                                Functions
 *************************************************************************************/

void jacobi_smooth(
    std::mdspan<double, std::extents<uint64_t, std::dynamic_extent, std::dynamic_extent, 1>> &f,
    const double h,
    std::mdspan<double, std::extents<uint64_t, std::dynamic_extent, std::dynamic_extent>> &u_dst,
    std::mdspan<double, std::extents<uint64_t, std::dynamic_extent, std::dynamic_extent>> &u_src) 
{
  double *const u_src_data{u_src.data_handle()};
  const int64_t _stride_u_src_0{u_src.stride(0)};
  const int64_t _stride_u_src_1{u_src.stride(1)};
  double *const u_dst_data{u_dst.data_handle()};
  const int64_t _stride_u_dst_0{u_dst.stride(0)};
  const int64_t _stride_u_dst_1{u_dst.stride(1)};
  double *const f_data{f.data_handle()};
  const int64_t _size_f_0{f.extents().extent(0)};
  const int64_t _size_f_1{f.extents().extent(1)};
  /* f.extents().extent(2) == 1 */
  const int64_t _stride_f_0{f.stride(0)};
  const int64_t _stride_f_1{f.stride(1)};
  kernels::kernel(_size_f_0, _size_f_1, _stride_f_0, _stride_f_1,
                  _stride_u_dst_0, _stride_u_dst_1, _stride_u_src_0,
                  _stride_u_src_1, f_data, h, u_dst_data, u_src_data);
}
```

````

The above is what we call a *generator script*; a Python script that, when executed, produces a pair
of source files of the same name, but with different extensions.
Generator scripts are the primary front-end pattern of *pystencils-sfg*; to learn more about them,
read the [Usage Guide](usage/generator_scripts.md).

## CMake Integration

*Pystencils-sfg* comes with a CMake module to register generator scripts for on-the-fly code generation.
With the module loaded, use the function `pystencilssfg_generate_target_sources` inside your `CMakeLists.txt`
to register one or multiple generator scripts; their outputs will automatically be added to the specified target.

```CMake
pystencilssfg_generate_target_sources( <target name> 
    SCRIPTS kernels.py ...
    FILE_EXTENSIONS .h .cpp
)
```

*Pystencils-sfg* makes sure that all generated files are on the project's include path.
To `#include` them, add the prefix `gen/<target name>`:

```C++
#include "gen/<target name>/kernels.h"
```

For details on how to add *pystencils-sfg* to your CMake project, refer to
[CLI and Build System Integration](usage/cli_and_build_system.md).
