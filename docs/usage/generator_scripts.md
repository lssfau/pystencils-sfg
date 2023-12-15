
Generator scripts are the primary way *pystencils-sfg* is meant to be used.
A generator script is a single Python script, say `kernels.py`, which contains *pystencils-sfg*
code at the top level such that, when executed, it emits source code to a pair of files `kernels.h`
and `kernels.cpp`. This guide describes how to write such a generator script, its structure, and how
it can be used to generate code.

This page gives a general overview over the code generation process, but introduces only the
convenient high-level interface provided by the [SourceFileGenerator][pystencilssfg.SourceFileGenerator]
and [SfgComposer][pystencilssfg.SfgComposer] classes.
For a more in-depth look into building source files, and about using *pystencils-sfg* outside
of a generator script, please take a look at the [In-Depth Guide](building.md).

## Anatomy

The code generation process in a generator script is controlled by the
[SourceFileGenerator][pystencilssfg.SourceFileGenerator] context manager.
It configures the code generator by combining configuration options from the 
environment (e.g. a CMake build system) with options specified in the script,
and infers the names of the output files from the script's name.
It then prepares and returns a code generation [context][pystencilssfg.SfgContext].
This context may then be passed to a [composer][pystencilssfg.SfgComposer],
which provides a convenient interface for constructing the source files.

To start, place the following code in a Python script, e.g. `kernels.py`:

```Python
from pystencilssfg import SourceFileGenerator, SfgConfiguration, SfgComposer

sfg_config = SfgConfiguration()
with SourceFileGenerator(sfg_config) as ctx:
    sfg = SfgComposer(ctx)

```

The source file is constructed within the context manager's managed region.
During execution of the script, when the region ends, a header/source file pair
`kernels.h` and `kernels.cpp` will be written to the file system next to your script.
Execute the script as-is and inspect the generated files, which will of course
still be empty.

A few notes on configuration:

 - The [SourceFileGenerator][pystencilssfg.SourceFileGenerator] parses the script's command line arguments
   for configuration options (refer to [CLI and Build System Integration](cli.md)).
   If you intend to use command-line parameters in your
   generation script, use [`sfg.context.argv`][pystencilssfg.SfgContext.argv] instead of `sys.argv`.
   There, all arguments meant for the code generator are already removed.
 - The code generator's configuration is consolidated from a global project configuration which may
   be provided by the build system; a number of command line arguments; and the
   [SfgConfiguration][pystencilssfg.SfgConfiguration] provided in the script.
   The project configuration may safely be overridden by the latter two; however, conflicts
   between command-line arguments and the configuration defined in the script will cause
   an exception to be thrown.

## Using the Composer

The object `sfg` constructed in above snippet is an instance of [SfgComposer][pystencilssfg.SfgComposer].
The composer is the central part of the user front-end of *pystencils-sfg*.
It provides an interface for constructing source files that attempts to closely mimic
C++ syntactic structures within Python.
Here is an overview of its various functions:

### Includes and Definitions

With [`SfgComposer.include`][pystencilssfg.SfgComposer.include], the code generator can be instructed
to include header files. 

```Python
with SourceFileGenerator(sfg_config) as ctx:
    sfg = SfgComposer(ctx)
    # ...
    sfg.include("<vector>")
    sfg.incldue("custom_header.h")
```

### Adding Kernels

`pystencils`-generated kernels are managed in
[kernel namespaces][pystencilssfg.source_components.SfgKernelNamespace].
The default kernel namespace is called `kernels` and is available via
[`SfgComposer.kernels`][pystencilssfg.SfgComposer.kernels].
Adding an existing `pystencils` AST, or creating one from a list of assignments, is possible
through [`add`][pystencilssfg.source_components.SfgKernelNamespace.add]
and [`create`][pystencilssfg.source_components.SfgKernelNamespace.create].
The latter is a wrapper around
[`pystencils.create_kernel`](
https://pycodegen.pages.i10git.cs.fau.de/pystencils/sphinx/kernel_compile_and_call.html#pystencils.create_kernel
).
Both functions return a [kernel handle][pystencilssfg.source_components.SfgKernelHandle]
through which the kernel can be accessed, e.g. for calling it in a function.

If required, use [`SfgComposer.kernel_namespace`][pystencilssfg.SfgComposer.kernel_namespace]
to access other kernel namespaces than the default one.

```Python
with SourceFileGenerator(sfg_config) as ctx:
    sfg = SfgComposer(ctx)
    # ...

    ast = ps.create_kernel(assignments, config)
    khandle = sfg.kernels.add(ast, "kernel_a")
    
    # is equivalent to
    
    khandle = sfg.kernels.create(assignments, "kernel_a", config)

    # You may use a different namespace
    nspace = sfg.kernel_namespace("group_of_kernels")
    nspace.create(assignments, "kernel_a", config)
```

### Building Functions

[Functions][pystencilssfg.source_components.SfgFunction] form the link between your `pystencils` kernels
and your C++ framework. A function in *pystencils-sfg* translates to a simple C++ function, and should
fulfill just the following tasks:

 - Extract kernel parameters (pointers, sizes, strides, numerical coefficients)
   from C++ objects (like fields, vectors, other data containers)
 - Call one or more kernels in sequence or in conditional branches

It is the philosophy of this project that anything more complicated than this should happen in handwritten
code; these generated functions are merely meant to close the remaining gap.

The composer provides an interface for constructing functions that tries to mimic the look of the generated C++
code.
Use [`SfgComposer.function`][pystencilssfg.SfgComposer.function] to create a function,
and [`SfgComposer.call`][pystencilssfg.SfgComposer.call] to call a kernel by its handle:

```Python
with SourceFileGenerator(sfg_config) as ctx:
    sfg = SfgComposer(ctx)
    # ...

    sfg.function("MyFunction")(
        sfg.call(khandle)
    )
```

Note the special syntax: To mimic the look of a C++ function, the composer uses a sequence of two calls
to construct the function.

The function body may further be populated with the following things:

#### Parameter Mappings

Extract kernel parameters from C++ objects:

 - [`map_param`][pystencilssfg.SfgComposer.map_param]: Add a single line of code to define one parameter
   depending on one other.
 - [`map_field`][pystencilssfg.SfgComposer.map_field] maps a pystencils
   [`Field`](https://pycodegen.pages.i10git.cs.fau.de/pystencils/sphinx/field.html)
   to a field data structure providing the necessary pointers, sizes and stride information.
   The field data structure must be provided as an instance of a subclass of
   [`SrcField`][pystencilssfg.source_concepts.SrcField].
   Currently, *pystencils-sfg* provides mappings to 
   [`std::vector`](https://en.cppreference.com/w/cpp/container/vector)
   (via [`std_vector_ref`][pystencilssfg.source_concepts.cpp.std_vector_ref])
   and
   [`std::mdspan`](https://en.cppreference.com/w/cpp/container/mdspan)
   (via [`mdspan_ref`][pystencilssfg.source_concepts.cpp.mdspan_ref])
   from the C++ standard library.
 - [`map_vector`][pystencilssfg.SfgComposer.map_vector] maps a sequence of scalar numerical values
   (given as `pystencils.TypedSymbol`s) to a vector data type. Currently, only `std::vector` is provided.

#### Conditional Branches

A conditonal branch may be added with [`SfgComposer.branch`][pystencilssfg.SfgComposer.branch]
using a special syntax:

```Python
with SourceFileGenerator(sfg_config) as ctx:
    sfg = SfgComposer(ctx)
    # ...
    
    sfg.function("myFunction")(
        # ...
        sfg.branch("condition")(
            # then-body
        )(
            # else-body (may be omitted)
        )
    )
    
```