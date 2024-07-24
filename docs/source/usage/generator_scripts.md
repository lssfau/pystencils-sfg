(guide:generator_scripts)=
# Generator Scripts

Writing generator scripts is the primary usage idiom of *pystencils-sfg*.
A generator script is a Python script, say `kernels.py`, which contains *pystencils-sfg*
code at the top level that, when executed, emits source code to a pair of files `kernels.h`
and `kernels.cpp`. This guide describes how to write such a generator script, its structure, and how
it can be used to generate code.

## Anatomy

The code generation process in a generator script is controlled by the `SourceFileGenerator` context manager.
It configures the code generator by combining configuration options from the 
environment (e.g. a CMake build system) with options specified in the script,
and infers the names of the output files from the script's name.
It then returns a {py:class}`composer <pystencilssfg.composer.SfgComposer>` to the user,
which provides a convenient interface for constructing the source files.

To start, place the following code in a Python script, e.g. `kernels.py`:

```{literalinclude} examples/guide_generator_scripts/01/kernels.py
```

The source file is constructed within the context manager's managed region.
During execution of the script, when the region ends, a header/source file pair
`kernels.h` and `kernels.cpp` will be written to disk next to your script.
Execute the script as-is and inspect the generated files, which will of course still be empty:

``````{dropdown} Generated Files
`````{tab-set}

````{tab-item} kernels.h
```{literalinclude} examples/guide_generator_scripts/01/kernels.h
```
````

````{tab-item} kernels.cpp
```{literalinclude} examples/guide_generator_scripts/01/kernels.cpp
```
````
`````
``````

<!-- A few notes on configuration:

 - The [SourceFileGenerator](#pystencilssfg.SourceFileGenerator) parses the script's command line arguments
   for configuration options (refer to [CLI and Build System Integration](cli_and_build_system.md)).
   If you intend to evaluate command-line parameters inside your
   generator script, read them from `sfg.context.argv` instead of `sys.argv`.
   There, all arguments meant for the code generator are already removed.
 - The code generator's configuration is consolidated from a global project configuration which may
   be provided by the build system; a number of command line arguments; and the
   [SfgConfiguration](#pystencilssfg.SfgConfiguration) provided in the script.
   The project configuration may safely be overridden by the latter two; however, conflicts
   between command-line arguments and the configuration defined in the script will cause
   an exception to be thrown. -->

## Using the Composer

The object `sfg` constructed in above snippet is an instance of [SfgComposer](#pystencilssfg.composer.SfgComposer).
The composer is the central part of the user front-end of *pystencils-sfg*.
It provides an interface for constructing source files that closely mimics
C++ syntactic structures within Python.
Here is an overview of its various functions:

### Includes and Definitions

With [`SfgComposer.include`](#pystencilssfg.composer.SfgBasicComposer.include), the code generator can be instructed to include header files.
As in C++, you can use the `<>` delimiters for system headers, and omit them for project headers.

`````{tab-set}

````{tab-item} kernels.py
```{literalinclude} examples/guide_generator_scripts/02/kernels.py
```
````

````{tab-item} kernels.h
```{literalinclude} examples/guide_generator_scripts/02/kernels.h
```
````

````{tab-item} kernels.cpp
```{literalinclude} examples/guide_generator_scripts/02/kernels.cpp
```
````
`````

### Adding Kernels

[pystencils](https://pycodegen.pages.i10git.cs.fau.de/pystencils/)-generated kernels are managed in *kernel namespaces*.
The default kernel namespace is called `kernels` and is available via
[`sfg.kernels`](#pystencilssfg.composer.SfgBasicComposer.kernels).
Adding an existing *pystencils* AST, or creating one from a list of assignments, is possible through 
[`kernels.add`](#pystencilssfg.ir.SfgKernelNamespace.add)
and
[`kernels.create`](#pystencilssfg.ir.SfgKernelNamespace.create).
The latter is a wrapper around
[`pystencils.create_kernel`](
https://pycodegen.pages.i10git.cs.fau.de/pystencils/sphinx/kernel_compile_and_call.html#pystencils.create_kernel
).
Both functions return a [kernel handle](#pystencilssfg.ir.SfgKernelHandle)
through which the kernel can be accessed, e.g. for calling it in a function.

To access other kernel namespaces than the default one,
the [`sfg.kernel_namespace`](#pystencilssfg.composer.SfgBasicComposer.kernel_namespace) method can be used.

`````{tab-set}

````{tab-item} kernels.py
```{literalinclude} examples/guide_generator_scripts/03/kernels.py
```
````

````{tab-item} kernels.h
```{literalinclude} examples/guide_generator_scripts/03/kernels.h
```
````

````{tab-item} kernels.cpp
```{literalinclude} examples/guide_generator_scripts/03/kernels.cpp
```
````
`````

### Building Functions

Through the composer, you can define free functions in your generated C++ file.
These may contain arbitrary code;
their primary intended task however is to wrap kernel calls with the necessary boilerplate code
to integrate them into a framework.
The composer provides an interface for constructing functions that tries to mimic the look of the generated C++ code.
Use `sfg.function` to create a function, and `sfg.call` to call a kernel:

`````{tab-set}

````{tab-item} kernels.py
```{literalinclude} examples/guide_generator_scripts/04/kernels.py
:start-after: start
:end-before: end
```
````

````{tab-item} kernels.h
```{literalinclude} examples/guide_generator_scripts/04/kernels.h
```
````

````{tab-item} kernels.cpp
```{literalinclude} examples/guide_generator_scripts/04/kernels.cpp
```
````
`````

Note the special syntax: To mimic the look of a C++ function, the composer uses a sequence of two calls
to construct the function.

The function body can furthermore be populated with code to embedd the generated kernel into
the target C++ application.
If you examine the generated files of the previous example, you will notice that your
function `scale_kernel` has lots of raw pointers and integer indices in its interface.
We can wrap those up into proper C++ data structures,
such as, for example, `std::span` or `std::vector`, like this:

`````{tab-set}

````{tab-item} kernels.py
```{literalinclude} examples/guide_generator_scripts/05/kernels.py
:start-after: start
:end-before: end
```
````

````{tab-item} kernels.h
```{literalinclude} examples/guide_generator_scripts/05/kernels.h
```
````

````{tab-item} kernels.cpp
```{literalinclude} examples/guide_generator_scripts/05/kernels.cpp
```
````
`````

If you now inspect the generated code, you will see that the interface of your function is
considerably simplified.
Also, all the necessary code was added to its body to extract the low-level information required
by the actual kernel from the data structures.

The `sfg.map_field` API can be used to map pystencils fields to a variety of different data structures.
The pystencils-sfg provides modelling support for a number of C++ standard library classes
(see {any}`pystencilssfg.lang.cpp.std`).
It also provides the necessary infrastructure for modelling the data structures of any C++ framework
in a similar manner.
