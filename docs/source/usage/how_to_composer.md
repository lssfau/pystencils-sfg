---
file_format: mystnb
kernelspec:
  name: python3
---

(composer_guide)=
# How To Use the Composer

```{code-cell} ipython3
:tags: [remove-cell]

import sys
from pathlib import Path

mockup_path = Path("../_util").resolve()
sys.path.append(str(mockup_path))

from sfg_monkeypatch import DocsPatchedGenerator  # monkeypatch SFG for docs

from pystencilssfg import SourceFileGenerator
```

The *composer API* is the interface by which C++ code is constructed in pystencils-sfg.
It is exposed through the ubiquitous *composer object* returned by the `SourceFileGenerator`
upon entry into its managed region.
This guide is meant to illustrate the various constructions possible through the composer,
starting from things as simple as `#include` directives and plain code strings,
up to entire classes and their members.

## Basic Functionality

### Prelude Comment

You can equip your generated files with a prelude comment that will be printed at their very top:

```{code-cell} ipython3
import datetime

now = datetime.datetime.now()

with SourceFileGenerator() as sfg:
    sfg.prelude(f"This file was generated using pystencils-sfg at {now}.")
```

### `#include` Directives

Use `sfg.include` to add `#include` directives to your generated files.
For a system-header include, delimit the header name with `<>`.
If the directive should be printed not into the header, but the implementation file,
set `private = True`:

```{code-cell} ipython3
with SourceFileGenerator() as sfg:
    sfg.include("my_header.hpp")
    sfg.include("<memory>")
    sfg.include("detail_header.hpp", private=True)
```

### Plain Code Strings

It is always possible to print out plain code strings verbatim.
Use `sfg.code()` to write code directly to the generated header file.
To emit the code to the implementation file instead, use `sfg.code(..., impl=True)`.

```{code-cell} ipython3
with SourceFileGenerator() as sfg:
    sfg.code("int THE_ANSWER;")
    sfg.code("int THE_ANSWER = 42;", impl=True)
```

## Defining Functions

Free functions can be declared and defined using the `sfg.function` sequencer.
It uses *builder syntax* to declare the various properties of the function in arbitrary
order via a sequence of calls. This sequence must end with a plain pair of parentheses `( ... )`
within which the function body will be defined.
For example, the following will create a function `getValue` with return type `int32` which is marked with the `nodiscard`
attribute:

```{code-cell} ipython3
with SourceFileGenerator() as sfg:
    sfg.function("getValue").returns("int32").attr("nodiscard")(
        "return 42;"
    )
```

For a list of all available function qualifiers, see the reference of {any}`SfgFunctionSequencer`.

### Populate the Function Body

The function body sequencer takes an arbitrary list of arguments of different types
which are then interpreted as C++ code.
The simplest case are plain strings, which will be printed out verbatim,
in order, each string argument on its own line:

```{code-cell} ipython3
with SourceFileGenerator() as sfg:
    sfg.function("factorial").params(
        sfg.var("n", "uint64")
    ).returns("uint64")(
        "if(n == 0) return 1;",
        "else return n * factorial(n - 1);"
    )
```

However, to make life easier, the composer API offers various APIs to model C++ code programmatically.

:::{note}
Observe that the code generated from the above snippet contains line breaks after the `if()` and `else` keywords
that where not part of the input.
This happens because `pystencils-sfg` passes its generated code through `clang-format` for beautification.
:::

#### Conditionals

To emit an if-else conditional statement, use {any}`sfg.branch <SfgBasicComposer.branch>`.
The syntax of `sfg.branch` mimics the C++ `if () {} else {}` construct by a sequence of
two (or three, with an `else`-branch) pairs of parentheses:

```{code-cell} ipython3
with SourceFileGenerator() as sfg:
    sfg.function("factorial").params(
        sfg.var("n", "uint64")
    ).returns("uint64")(
        sfg.branch("n == 0")(  # Condition
            #   then-block
            "return 1;"
        )(
            #   else-block
            "return n * factorial(n - 1);"
        )
    )
```

#### Variables and Automatic Collection of Function Parameters

Pystencils-sfg's versatile expression system can keep track of free variables
in a function body, and then automatically exposes these variables as function parameters.
To cast a code string as an expression depending on variables, we need to do two things:

 - Create an object for each variable using {any}`sfg.var <SfgBasicComposer.var>`.
   This method takes the name and data type of the variable.
 - Create the expression through {any}`sfg.expr <SfgBasicComposer.expr>` by interpolating a
   Python format string (see {any}`str.format`) with variables or other expressions.

For example, here's the expression in the `else`-block of the `factorial` function modelled this way:

```{code-block} python
n = sfg.var("n", "uint64")
...
sfg.expr("return {0} * factorial({0} - 1);", n)
```

Using this, we can omit the manually specified parameter list for `factorial`:

```{code-cell} ipython3
with SourceFileGenerator() as sfg:
    n = sfg.var("n", "uint64")

    sfg.function("factorial").returns("uint64")(
        sfg.branch(sfg.expr("{} == 0", n))(  # Condition
            #   then-block
            "return 1;"
        )(
            #   else-block, with interpolated expression
            sfg.expr("return {0} * factorial({0} - 1);", n)
        )
    )
```

#### Manual Parameter Lists

When function parameters are collected from the function body, the composer will always order them
alphabetically. If this is not desired, e.g. if a generated function is expected to have a specific interface
with a fixed parameter order, you will need to specify the parameter list manually using `.params(...)`.

#### Variables of C++ Class Type

`sfg.var` should only be used for the most basic data types: it parses its second argument as a data type using
{any}`create_type <pystencils.types.create_type>`, which is restricted to primitive and fixed-width C types.
For more complex C++ classes, class templates, and their APIs, pystencils-sfg provides its own modelling system,
implemented in `pystencilssfg.lang`.
This system is used, for instance, by `pystencilssfg.lang.cpp.std`, which mirrors (a small part of) the C++ standard library.

:::{seealso}
[](#how_to_cpp_api_modelling)
:::

To create a variable of a class template represented using the `pystencilssfg.lang` modelling system,
first instantiate the class (with any template arguments, as well as optional `const` and `ref` qualifiers)
and then call `var` on it:

```{code-cell} ipython3
from pystencilssfg.lang.cpp import std

data = std.vector("float64", const=True, ref=True).var("data")
str(data), str(data.dtype)
```

#### Initializing Variables

To emit an initializer statement for a variable, use `sfg.init`:

```{code-block} python
from pystencilssfg.lang.cpp import std

result = std.tuple("int32", "int32").var("result")
n, m = sfg.vars("n, m", "int32")

sfg.init(result)(
    sfg.expr("{} / {}", n, m),
    sfg.expr("{} % {}", n, m)
)
```

This will be recognized by the parameter collector:
variables that are defined using `init` before they are used will be considered *bound*
and will not end up in the function signature.
Also, any variables passed to the braced initializer-expression (by themselves or inside `sfg.expr`)
will be found and tracked by the parameter collector:

```{code-cell} ipython3
from pystencilssfg.lang.cpp import std

with SourceFileGenerator() as sfg:
    result = std.tuple("int32", "int32").var("result")
    n, m = sfg.vars("n, m", "int32")

    sfg.function("div_rem").params(n, m).returns(result.dtype)(
        sfg.init(result)(
            sfg.expr("{} / {}", n, m),
            sfg.expr("{} % {}", n, m)
        ),
        sfg.expr("return {}", result)
    )
```

(how_to_namespaces)=
## Namespaces

C++ uses namespaces to structure code and group entities.
By default, pystencils-sfg emits all code into the global namespace.
For instructions on how to change the outermost namespace used by the `SourceFileGenerator`,
see [](#how_to_generator_scripts_config).

Starting from the outermost namespace, nested namespaces can be entered and exited during
code generation.
To enter a new namespace, use `sfg.namespace` in one of two ways:

 - Simply calling `sfg.namespace("my_namespace")` and ignoring its return value will cause the
   generator script to use the given namespace for the rest of its execution;
 - Calling `sfg.namespace("my_namespace")` in a `with` statement will activate the given namespace
   only for the duration of the managed block.

To illustrate, the following snippet activates the namespace `mylib::generated` for the entire
length of the generator script, and then enters and exits the nested namespace `mylib::generated::detail`:

```{code-cell} ipython3
with SourceFileGenerator() as sfg:
    sfg.namespace("mylib::generated")

    sfg.code("/* Generated code in outer namespace */")

    with sfg.namespace("detail"):
        sfg.code("/* Implementation details in the inner namespace */")

    sfg.code("/* More code in the outer namespace */")
```

## Kernels and Parameter Mappings

The original purpose of pystencils-sfg is to simplify the embedding of *pystencils*-generated
numerical kernels into C++ applications.
This section discusses how to register kernels with the source file generator,
how to call them in wrapper code,
and how to automatically map symbolic pystencils fields onto nd-array data structures.

### Registering Kernels

In the generated files, kernels are organized in *kernel namespaces*.
The composer gives us access to the default kernel namespace (`<current_namespace>::kernels`)
via `sfg.kernels`.

To add a kernel,
 - either pass its assignments and the pystencils code generator configuration directly to {any}`kernels.create() <KernelsAdder.create>`,
 - or create the kernel separately through {any}`pystencils.create_kernel <pystencils.codegen.create_kernel>` and register it using
   {any}`kernels.add() <KernelsAdder.add>`.

Both functions return a kernel handle, through which the kernel may later be invoked.

You may create and access custom-named kernel namespaces using {any}`sfg.kernel_namespace() <SfgBasicComposer.kernel_namespace>`.
This gives you a {any}`KernelsAdder` object with the same interface as `sfg.kernels`.

:::{note}

A kernel namespace is not a regular namespace; if you attempt to create both a regular and a kernel namespace with the same name,
the composer will raise an error.
:::

Here's an example with two kernels being registered in different kernel namespace,
once using `add`, and once using `create`.

```{code-cell} ipython3
import pystencils as ps

with SourceFileGenerator() as sfg:
    #   Create symbolic fields
    f, g = ps.fields("f, g: double[2D]")

    #   Define and create the first kernel
    asm1 = ps.Assignment(f(0), g(0))
    cfg1 = ps.CreateKernelConfig()
    cfg1.cpu.openmp.enable = True
    khandle_1 = sfg.kernels.create(asm1, "first_kernel", cfg1)

    #   Define the second kernel and its codegen configuration
    asm2 = ps.Assignment(f(0), 3.0 * g(0))
    cfg2 = ps.CreateKernelConfig(target=ps.Target.CUDA)

    #   Create and register the second kernel at a custom namespace
    kernel2 = ps.create_kernel(asm2, cfg2)
    khandle_2 = sfg.kernel_namespace("gpu_kernels").add(kernel2, "second_kernel")
```

### Writing Kernel Wrapper Functions

By default, kernel definitions are only visible in the generated implementation file;
kernels are supposed to not be called directly, but through wrapper functions.
This serves to hide their fairly lenghty and complicated low-level function interface.

#### Invoking CPU Kernels

To call a CPU kernel from a function, use `sfg.call` on a kernel handle:

```{code-block} python
sfg.function("kernel_wrapper")(
    sfg.call(khandle)
)
```

This will expose all parameters of the kernel into the wrapper function and, in turn,
cause them to be added to its signature.
We don't want to expose this complexity, but instead hide it by using appropriate data structures.
The next section explains how that is achieved in pystencils-sfg.

#### Mapping Fields to Data Structures

Pystencils kernels operate on n-dimensional contiguous or strided arrays,
There exist many classes with diverse APIs modelling such arrays throughout the scientific
computing landscape, including [Kokkos Views][kokkos_view], [C++ std::mdspan][mdspan],
[SYCL buffers][sycl_buffer], and many framework-specific custom-built classes.
Using the protocols behind {any}`sfg.map_field <SfgBasicComposer.map_field>`,
it is possible to automatically emit code
that extracts the indexing information required by a kernel from any of these classes,
as long as a suitable API reflection is available.

:::{seealso}
[](#field_data_structure_reflection) for instructions on how to set up field API
reflection for a custom nd-array data structure.
:::

Pystencils-sfg natively provides field extraction for a number of C++ STL-classes,
such as `std::vector` and `std::span` (for 1D fields) and `std::mdspan`.
Import any of them from `pystencilssfg.lang.cpp.std` and create an instance for a given
field using `.from_field()`.
Then, inside the wrapper function, pass the symbolic field and its associated data structure to
{any}`sfg.map_field <SfgBasicComposer.map_field>`.
before calling the kernel:

```{code-cell} ipython3
import pystencils as ps
from pystencilssfg.lang.cpp import std

with SourceFileGenerator() as sfg:
    #   Create symbolic fields
    f, g = ps.fields("f, g: double[1D]")

    #   Create data structure reflections
    f_vec = std.vector.from_field(f)
    g_span = std.span.from_field(g)

    #   Create the kernel
    asm = ps.Assignment(f(0), g(0))
    khandle = sfg.kernels.create(asm, "my_kernel")

    #   Create the wrapper function
    sfg.function("call_my_kernel")(
        sfg.map_field(f, f_vec),
        sfg.map_field(g, g_span),
        sfg.call(khandle)
    )
```

## GPU Kernels

Pystencils also allows us to generate kernels for the CUDA and HIP GPU programming models.
This section describes how to generate GPU kernels through pystencils-sfg;
how to invoke them with various launch configurations,
and how GPU execution streams are reflected.

### Generate and Invoke CUDA and HIP Kernels

To generate a kernel targetting either of these, set the
{any}`target <pystencils.codegen.config.CreateKernelConfig.target>`
code generator option to either `Target.CUDA` or `Target.HIP`.
After registering a GPU kernel,
its invocation can be rendered using {any}`sfg.gpu_invoke <SfgGpuComposer.gpu_invoke>`.
Here is an example using CUDA:

```{code-cell} ipython3
from pystencilssfg import SfgConfig
sfg_config = SfgConfig()
sfg_config.extensions.impl = "cu"

with SourceFileGenerator(sfg_config) as sfg:
    #   Configure the code generator to use CUDA
    cfg = ps.CreateKernelConfig(target=ps.Target.CUDA)

    #   Create fields, assemble assignments
    f, g = ps.fields("f, g: double[128, 128]")
    asm = ps.Assignment(f(0), g(0))

    #   Register kernel
    khandle = sfg.kernels.create(asm, "gpu_kernel", cfg)

    #   Invoke it
    sfg.function("kernel_wrapper")(
        sfg.gpu_invoke(khandle)
    )
```

In this snippet, we used the [generator configuration](#how_to_generator_scripts_config)
to change the suffix of the generated implementation file to `.cu`.

When investigating the generated `.cu` file, you can see that the GPU launch configuration parameters
*grid size* and *block size* are being computed automatically from the array sizes.
This behavior can be changed by modifying options in the {any}`gpu <pystencils.codegen.config.GpuOptions>`
category of the `CreateKernelConfig`.

### Adapting the Launch Configuration

GPU kernel invocations usually require the user to provide a launch grid, defined
by the GPU thread block size and the number of blocks on the grid.
In the simplest case (seen above), pystencils-sfg will emit code that automatically
computes these parameters from the size of the arrays passed to the kernel,
using a default block size defined by pystencils.

The code generator also permits customization of the launch configuration.
You may provide a custom block size to override the default, in which case the
grid size will still be computed by dividing the array sizes by your block size.
Otherwise, you can also fully take over control of both block and grid size.
For both cases, instructions are given in the following.

#### User-Defined Block Size for Auto-Computed Grid Size

To merely modify the block size argument while still automatically inferring the grid size,
pass a variable or expression of type `dim3` to the `block_size` parameter of `gpu_invoke`.
Pystencils-sfg exposes two versions of `dim3`, which differ primarily in their associated
runtime headers:

 - {any}`pystencilssfg.lang.gpu.cuda.dim3 <CudaAPI.dim3>` for CUDA, and
 - {any}`pystencilssfg.lang.gpu.hip.dim3 <HipAPI.dim3>` for HIP.

The following snippet selects the correct `dim3` type according to the kernel target;
it then creates a variable of that type and turns that into an argument to the kernel invocation:

```{code-cell} ipython3
:tags: [remove-cell]
target = ps.Target.HIP
cfg = ps.CreateKernelConfig(target=target)
f, g = ps.fields("f, g: double[128, 128]")
asm = ps.Assignment(f(0), g(0))
```

```{code-cell} ipython3
from pystencilssfg.lang.gpu import hip

with SourceFileGenerator(sfg_config) as sfg:
    # ... define kernel ...
    khandle = sfg.kernels.create(asm, "gpu_kernel", cfg)

    #   Select dim3 reflection
    match target:
        case ps.Target.CUDA:
            from pystencilssfg.lang.gpu import cuda as gpu_api
        case ps.Target.HIP:
            from pystencilssfg.lang.gpu import hip as gpu_api
    
    #   Create dim3 variable and pass it to kernel invocation
    block_size = gpu_api.dim3(const=True).var("block_size")

    sfg.function("kernel_wrapper")(
        sfg.gpu_invoke(khandle, block_size=block_size)
    )
```

#### Manual Launch Configurations

To take full control of the launch configuration, we must disable its automatic inferrence
by setting the {any}`gpu.manual_launch_grid <pystencils.codegen.config.GpuOptions.manual_launch_grid>`
code generator option to `True`.
Then, we must pass `dim3` arguments for both `block_size` and `grid_size` to the kernel invocation:

```{code-cell} ipython3
from pystencilssfg.lang.gpu import hip

with SourceFileGenerator(sfg_config) as sfg:
    # ... define kernel ...

    #   Configure for manual launch config
    cfg = ps.CreateKernelConfig(target=ps.Target.CUDA)
    cfg.gpu.manual_launch_grid = True

    #   Register kernel
    khandle = sfg.kernels.create(asm, "gpu_kernel", cfg)
    
    #   Create dim3 variables
    from pystencilssfg.lang.gpu import cuda
    block_size = cuda.dim3(const=True).var("block_size")
    grid_size = cuda.dim3(const=True).var("grid_size")

    sfg.function("kernel_wrapper")(
        sfg.gpu_invoke(khandle, block_size=block_size, grid_size=grid_size)
    )
```

### Using Streams

CUDA and HIP kernels can be enqueued into streams for concurrent execution.
This is mirrored in pystencils-sfg;
all overloads of `gpu_invoke` take an optional `stream` argument.
The `stream_t` data types of both CUDA and HIP are made available
through the respective API reflections:

 - {any}`lang.gpu.cuda.stream_t <CudaAPI.stream_t>` reflects `cudaStream_t`, and
 - {any}`lang.gpu.hip.stream_t <HipAPI.stream_t>` reflects `hipStream_t`.

Here is an example that creates a variable of the HIP stream type
and passes it to `gpu_invoke`:

```{code-cell} ipython3
:tags: [remove-cell]
cfg = ps.CreateKernelConfig(target=ps.Target.HIP)
f, g = ps.fields("f, g: double[128, 128]")
asm = ps.Assignment(f(0), g(0))
```

```{code-cell} ipython3
from pystencilssfg.lang.gpu import hip

with SourceFileGenerator(sfg_config) as sfg:
    # ... define kernel ...
    khandle = sfg.kernels.create(asm, "gpu_kernel", cfg)

    stream = hip.stream_t(const=True).var("stream")

    sfg.function("kernel_wrapper")(
        sfg.gpu_invoke(khandle, stream=stream)
    )
```

:::{admonition} To Do

 - Defining classes, their fields constructors, and methods

:::


[kokkos_view]: https://kokkos.org/kokkos-core-wiki/ProgrammingGuide/View.html
[mdspan]: https://en.cppreference.com/w/cpp/container/mdspan
[sycl_buffer]: https://registry.khronos.org/SYCL/specs/sycl-2020/html/sycl-2020.html#subsec:buffers
