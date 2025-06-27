---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.16.4
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
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

DocsPatchedGenerator.setup("generated", False, True, "mdspan_demo")
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
    src_mdspan = std.mdspan.from_field(src, layout_policy="layout_left")
    dst_mdspan = std.mdspan.from_field(dst, layout_policy="layout_left")

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

## Integrating and Compiling the Generated Code

To use the generated functions from handwritten code, include the generated header file
into your C++ application, compile the generated translation unit to an object file,
and link the two together.

Here is an example application frame:

```{code-cell} ipython3
:tags: [remove-input]

from IPython.display import Markdown

output_dir = Path("mdspan_demo")
output_dir.mkdir(exist_ok=True)

code = r"""
#include <mdspan>
#include <memory>
#include <iostream>

// Include the generated header
#include "generated.hpp"

using field_t = std::mdspan< double, std::dextents< uint64_t, 1 >, std::layout_left >;

int main(void){
    constexpr size_t N = 4;
    auto data_src = std::make_unique< double[] >(N);
    auto data_dst = std::make_unique< double[] >(N);

    field_t src { data_src.get(), N };
    field_t dst { data_dst.get(), N };

    for(size_t i = 0; i < N; ++i)
        src[i] = 2.0 * double(i) + 1.0;

    const double c { 4.5 };

    // Call generated function
    scale(c, dst, src);

    // Print output
    for(size_t i = 0; i < N; ++i)
        std::cout << dst[i] << std::endl;

    return 0;
}
"""
(output_dir / "app.cpp").write_text(code)

md = f""":::{{code-block}} C++
:caption: app.cpp

{code}

:::
"""

Markdown(md)
```

The application sets up the data arrays and `mdspan`
views for the `src` and `dst` fields, and initializes `src`.
Then, it invokes the `scale` kernel defined in the above generator script
on these `mdspan` objects and prints the result to stdout.

Save the code into a file `app.cpp`.
We can now compile application frame and generated code together, and link them into an executable,
using the following compiler command:

```{code-block} bash
clang++ -std=c++23 -stdlib=libc++ -I $(python -m pystencils.include -s) generated.cpp app.cpp
```

Let's briefly take a look at the compiler options:
- `std=c++23` ensures the C++23 standard, required for `std::mdspan`;
- `-stdlib=libc++` instructs `clang` to link against the [LLVM C++ standard library](https://libcxx.llvm.org/),
  which implements `std::mdspan`;
- `-I $(python -m pystencils.include -s)` adds the location of the pystencils runtime headers to the compiler's include path;
  the header path is obtained by executing the `python -m pystencils.include -s` subcommand.

:::{note}
The above command requires that at least clang 18 and `libc++` are installed.
On Ubuntu >= 24, you can install these via `apt-get install clang libc++-dev`.
On older systems, install `clang-18 libc++-18-dev` instead.
:::

After succesful compilation, running the executable should yield the following output:

```{code-block} bash
./a.out
```

```{code-cell} ipython3
:tags: [remove-input]

!cd mdspan_demo; clang++ -std=c++23 -stdlib=libc++ -I $(python -m pystencils.include -s) generated.cpp app.cpp
!./mdspan_demo/a.out
```

That's it! We've now gone through all the basic steps of generating code
and integrating it into an application using pystencils-sfg.

## Next Steps

To learn more about using pystencils-sfg's composer API, read [](#composer_guide).
For integrating reflection of your own C++ APIs and field classes in pystencils-sfg,
refer to [](#how_to_cpp_api_modelling).
At [](#guide_project_integration), you can find more information about integrating pystencils-sfg
with your project and build system to run code generation on-the-fly.

[mdspan]: https://en.cppreference.com/w/cpp/container/mdspan
[cppreference_compiler_support]: https://en.cppreference.com/w/cpp/compiler_support
