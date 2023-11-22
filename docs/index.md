# The pystencils Source File Generator

A bridge over the semantic gap between code emitted by [pystencils](https://pypi.org/project/pystencils/)
and your C/C++/Cuda/HIP framework.

## Installation

### From Git

Clone the [repository](https://i10git.cs.fau.de/da15siwa/pystencils-sfg) and install the package into your current Python environment
(usage of virtual environments is strongly encouraged!):

```bash
git clone https://i10git.cs.fau.de/da15siwa/pystencils-sfg.git
cd pystencils-sfg
pip install .
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

from pystencilssfg import SourceFileGenerator
from pystencilssfg.source_concepts.cpp import mdspan_ref

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

Take this code, store it into a file `poisson_smoother.py`, and enter the magic words into a terminal:

```shell
python poisson_smoother.py
```

This command will execute the code generator through the `SourceFileGenerator` context manager.
The code generator takes the name of your Python script, replaces `.py` with `.cpp` and `.h`, and writes
`poisson_smoother.cpp` and `poisson_smoother.h` into the current directory, ready to be `#include`d.
