# The pystencils Source File Generator

[![](https://i10git.cs.fau.de/pycodegen/pystencils-sfg/badges/master/pipeline.svg)](https://i10git.cs.fau.de/pycodegen/pystencils-sfg/commits/master)
[![](https://img.shields.io/gitlab/license/pycodegen%2Fpystencils-sfg?gitlab_url=https%3A%2F%2Fi10git.cs.fau.de)](https://i10git.cs.fau.de/pycodegen/pystencils-sfg/-/blob/master/LICENSE)

A bridge over the semantic gap between code emitted by [pystencils](https://pypi.org/project/pystencils/)
and your C/C++/Cuda/HIP framework.

## Installation

### From Git

Install the package into your current Python environment from the git repository using pip
(usage of virtual environments is strongly encouraged!):

```bash
pip install git+https://i10git.cs.fau.de/pycodegen/pystencils-sfg.git
```

### From PyPI

Not yet available.

## Primer

With *pystencils-sfg*, including your *pystencils*-generated kernels with handwritten code becomes straightforward
and intuitive. To illustrate, generating a Jacobi smoother for the two-dimensional Poisson equation
and mapping it onto C++23 `std::mdspan`s takes just a few lines of code:

```python
import sympy as sp

from pystencils import fields, kernel

from pystencilssfg import SourceFileGenerator, SfgComposer
from pystencilssfg.source_concepts.cpp import mdspan_ref

with SourceFileGenerator() as ctx:
    sfg = SfgComposer(ctx)

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

Take this code, store it into a file `poisson_smoother.py`, and enter the magic words into a terminal:

```shell
python poisson_smoother.py
```

This command will execute the code generator through the `SourceFileGenerator` context manager.
The code generator takes the name of your Python script, replaces `.py` with `.cpp` and `.h`, and writes
`poisson_smoother.cpp` and `poisson_smoother.h` into the current directory, ready to be `#include`d.

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
