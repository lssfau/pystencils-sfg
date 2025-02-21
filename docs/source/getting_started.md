---
file_format: mystnb
kernelspec:
  name: python3
---

(getting_started_guide)=
# Getting Started

```{code-cell} ipython3
:tags: [remove-cell]

import sys
from pathlib import Path

mockup_path = Path("_util").resolve()
sys.path.append(str(mockup_path))

from sfg_monkeypatch import DocsPatchedGenerator  # monkeypatch SFG for docs
```


This guide will explain the basics of using pystencils-sfg through generator scripts.
Generator scripts are the primary way to run code generation with pystencils-sfg.
A generator script is a Python script that, when executed, produces one or more
C++ source files with the same base name, but different file extensions.

## Writing a Basic Generator Script

To start using pystencils-sfg, create a new empty Python file and populate it with the
following minimal skeleton:

```{code-block} python
from pystencilssfg import SourceFileGenerator

with SourceFileGenerator() as sfg:
    ...
```

The above snippet defines the basic structure of a *generator script*.
When executed, the above will produce two (nearly) empty C++ files
in the current folder, both with the same name as your Python script
but with `.hpp` and `.cpp` file extensions instead.

In the generator script, code generation is orchestrated by the `SourceFileGenerator` context manager.
When entering into the region controlled by the `SourceFileGenerator`,
it supplies us with a *composer object*, customarily called `sfg`.
Through the composer, we can declaratively populate the generated files with code.

## Adding a pystencils Kernel

One of the core applications of pystencils-sfg is to generate and wrap pystencils-kernels
for usage within C++ applications.
To register a kernel, pass its assignments to `sfg.kernels.create`, which returns a *kernel handle* object:

```{code-block} python
src, dst = ps.fields("src, dst: double[1D]")
c = sp.Symbol("c")

@ps.kernel
def scale():
    dst.center @= c * src.center()

#   Register the kernel for code generation
scale_kernel = sfg.kernels.create(scale, "scale_kernel")
```

In order to call the kernel, and expose it to the outside world,
we have to create a wrapper function for it, using `sfg.function`.
In its body, we use `sfg.call` to invoke the kernel:

```{code-block} python
sfg.function("scale")(
    sfg.call(scale_kernel)
)
```

The `function` composer has a special syntax that mimics the generated C++ code.
We call it twice in sequence,
first providing the name of the function, and then populating its body.

Here's our full first generator script:

```{code-cell} ipython3
:tags: [remove-cell]

DocsPatchedGenerator.scriptname = "add_kernel_demo"
DocsPatchedGenerator.glue = True
DocsPatchedGenerator.display = False
```

```{code-cell} ipython3
from pystencilssfg import SourceFileGenerator
import pystencils as ps
import sympy as sp

with SourceFileGenerator() as sfg:
    #   Define a copy kernel
    src, dst = ps.fields("src, dst: double[1D]")
    c = sp.Symbol("c")

    @ps.kernel
    def scale():
        dst.center @= c * src.center()

    #   Register the kernel for code generation
    scale_kernel = sfg.kernels.create(scale, "scale_kernel")

    #   Wrap it in a function
    sfg.function("scale")(
        sfg.call(scale_kernel)
    )

```

When executing the above script, two files will be generated: a C++ header and implementation file containing
the `scale_kernel` and its wrapper function:

:::{glue:md} sfg_out_add_kernel_demo
:format: myst
:::

As you can see, the header file contains a declaration `void scale(...)` of a function
which is defined in the associated implementation file,
and there calls our generated numerical kernel.
As of now, it forwards the entire set of low-level kernel arguments -- array pointers and indexing information --
to the outside.
In numerical applications, this information is most of the time hidden from the user by encapsulating
it in high-level C++ data structures.
Pystencils-sfg offers means of representing such data structures in the code generator, and supports the
automatic extraction of the low-level indexing information from them.

## Mapping Fields to Data Structures

Since C++23 there exists the archetypical [std::mdspan][mdspan], which represents a non-owning n-dimensional view
on a contiguous data array.
Pystencils-sfg offers native support for mapping pystencils fields onto `mdspan` instances in order to
hide their memory layout details.

Import `std` from `pystencilssfg.lang.cpp` and use `std.mdspan.from_field` to create representations
of your pystencils fields as `std::mdspan` objects:

```{code-block} python
from pystencilssfg.lang.cpp import std

...

src_mdspan = std.mdspan.from_field(src)
dst_mdspan = std.mdspan.from_field(dst)
```

Then, inside the wrapper function, instruct the SFG to map the fields onto their corresponding mdspans:

```{code-block} python
sfg.function("scale")(
    sfg.map_field(src, src_mdspan),
    sfg.map_field(dst, dst_mdspan),
    sfg.call(scale_kernel)
)
```

Here's the full script and its output:

```{code-cell} ipython3
:tags: [remove-cell]

DocsPatchedGenerator.setup("mdspan_demo", False, True)
```


```{code-cell} ipython3
from pystencilssfg import SourceFileGenerator
import pystencils as ps
import sympy as sp

from pystencilssfg.lang.cpp import std

with SourceFileGenerator() as sfg:
    #   Define a copy kernel
    src, dst = ps.fields("src, dst: double[1D]")
    c = sp.Symbol("c")

    @ps.kernel
    def scale():
        dst.center @= c * src.center()

    #   Register the kernel for code generation
    scale_kernel = sfg.kernels.create(scale, "scale_kernel")

    #   Create mdspan objects
    src_mdspan = std.mdspan.from_field(src)
    dst_mdspan = std.mdspan.from_field(dst)

    #   Wrap it in a function
    sfg.function("scale")(
        sfg.map_field(src, src_mdspan),
        sfg.map_field(dst, dst_mdspan),
        sfg.call(scale_kernel)
    )

```

:::{note}

As of early 2025, `std::mdspan` is still not fully adopted by standard library implementors
(see [cppreference.com][cppreference_compiler_support]);
most importantly, the GNU libstdc++ does not yet ship an implementation of it.
However, a reference implementation is available at https://github.com/kokkos/mdspan.
If you are using the reference implementation, refer to the documentation of {any}`StdMdspan`
for advice on how to configure the header file and namespace where the class is defined.
:::


[mdspan]: https://en.cppreference.com/w/cpp/container/mdspan
[cppreference_compiler_support]: https://en.cppreference.com/w/cpp/compiler_support
