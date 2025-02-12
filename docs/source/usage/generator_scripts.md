(guide:generator_scripts)=
# Generator Scripts

Writing generator scripts is the primary usage idiom of *pystencils-sfg*.
A generator script is a Python script, say `kernels.py`, which contains *pystencils-sfg*
code at the top level that, when executed, emits source code to a pair of files `kernels.hpp`
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
`kernels.hpp` and `kernels.cpp` will be written to disk next to your script.
Execute the script as-is and inspect the generated files, which will of course still be empty:

``````{dropdown} Generated Files
`````{tab-set}

````{tab-item} kernels.hpp
```{literalinclude} examples/guide_generator_scripts/01/kernels.hpp
```
````

````{tab-item} kernels.cpp
```{literalinclude} examples/guide_generator_scripts/01/kernels.cpp
```
````
`````
``````

## Using the Composer

The object `sfg` constructed in above snippet is an instance of [SfgComposer](#pystencilssfg.composer.SfgComposer).
The composer is the central part of the user front-end of *pystencils-sfg*.
It provides an interface for constructing source files that closely mimics
C++ syntactic structures within Python.

::::{dropdown} Composer API Overview
```{eval-rst}
.. currentmodule:: pystencilssfg.composer
```

Structure and Verbatim Code:

```{eval-rst}

.. autosummary::
  :nosignatures:

  SfgBasicComposer.prelude
  SfgBasicComposer.include
  SfgBasicComposer.namespace
  SfgBasicComposer.code
```

Kernels and Kernel Namespaces:

```{eval-rst}

.. autosummary::
  :nosignatures:

  SfgBasicComposer.kernels
  SfgBasicComposer.kernel_namespace
  SfgBasicComposer.kernel_function
```

Function definition, parameters, and header inclusion:

```{eval-rst}

.. autosummary::
  :nosignatures:

  SfgBasicComposer.function
  SfgBasicComposer.params
  SfgBasicComposer.require
```

Variables, expressions, and variable initialization:

```{eval-rst}

.. autosummary::
  :nosignatures:

  SfgBasicComposer.var
  SfgBasicComposer.vars
  SfgBasicComposer.expr
  SfgBasicComposer.init
  
  SfgBasicComposer.map_field
  SfgBasicComposer.set_param
```

Parameter mappings:

```{eval-rst}

.. autosummary::
  :nosignatures:

  SfgBasicComposer.set_param
  SfgBasicComposer.map_field
  SfgBasicComposer.map_vector
```

Control Flow:

```{eval-rst}

.. autosummary::
  :nosignatures:

  SfgBasicComposer.branch
  SfgBasicComposer.switch
```

Kernel Invocation:

```{eval-rst}

.. autosummary::
  :nosignatures:

  SfgBasicComposer.call
  SfgBasicComposer.cuda_invoke
```
::::

### Includes and Definitions

With {any}`include <SfgBasicComposer.include>`, the code generator can be instructed to include header files.
As in C++, you can use the `<>` delimiters for system headers, and omit them for project headers.

`````{tab-set}

````{tab-item} kernels.py
```{literalinclude} examples/guide_generator_scripts/02/kernels.py
```
````

````{tab-item} kernels.hpp
```{literalinclude} examples/guide_generator_scripts/02/kernels.hpp
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

````{tab-item} kernels.hpp
```{literalinclude} examples/guide_generator_scripts/03/kernels.hpp
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

````{tab-item} kernels.hpp
```{literalinclude} examples/guide_generator_scripts/04/kernels.hpp
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

````{tab-item} kernels.hpp
```{literalinclude} examples/guide_generator_scripts/05/kernels.hpp
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


## Configuration and Invocation

There are several ways to affect the behavior and output of a generator script.
For one, the `SourceFileGenerator` itself may be configured from the combination of three
different configuration sources:

- **Inline Configuration:** The generator script may set up an {any}`SfgConfig` object,
  which is passed to the `SourceFileGenerator` at its creation; see [Inline Configuration](#inline_config)
- **Command-Line Options:** The `SourceFileGenerator` parses the command line arguments of
  the generator script to set some of its configuration options; see [Command-Line Options](#cmdline_options)
- **Project Configuration:** When embedded into a larger project, using a build system such as CMake, generator scripts
  may be configured globally within that project by the use of a *configuration module*.
  Settings specified inside that configuration module are always overridden by the former to configuration sources.
  For details on configuration modules, refer to the guide on [Project and Build System Integration](#guide_project_integration).

(inline_config)=
### Inline Configuration

To configure the source file generator within your generator script, import the {any}`SfgConfig` from `pystencilssfg`.
You may then set up the configuration object before passing it to the `SourceFileGenerator` constructor.
To illustrate, the following snippet alters the code indentation width and changes the output directory
of the generator script to `gen_src`:

```{literalinclude} examples/guide_generator_scripts/inline_config/kernels.py
```

(cmdline_options)=
### Command-Line Options

The `SourceFileGenerator` consumes a number of command-line parameters that may be passed to the script
on invocation. These include:

- `--sfg-output-dir <path>`: Set the output directory of the generator script. This corresponds to {any}`SfgConfig.output_directory`.
- `--sfg-file-extensions <exts>`: Set the file extensions used for the generated files;
  `exts` must be a comma-separated list not containing any spaces. Corresponds to {any}`SfgConfig.extensions`.
- `--sfg-output-mode <mode>`: Set the output mode of the generator script. Corresponds to {any}`SfgConfig.output_mode`.

If any configuration option is set to conflicting values on the command line and in the inline configuration,
the generator script will terminate with an error.

You may examine the full set of possible command line parameters by invoking a generator script
with the `--help` flag:

```bash
$ python kernels.py --help
```

(custom_cli_args)=
## Adding Custom Command-Line Options

Sometimes, you might want to add your own command-line options to a generator script
in order to affect its behavior from the shell,
for instance by using {any}`argparse` to set up an argument parser.
If you parse your options directly from {any}`sys.argv`,
as {any}`parse_args <argparse.ArgumentParser.parse_args>` does by default,
your parser will also receive any options meant for the `SourceFileGenerator`.
To filter these out of the argument list,
pass the additional option `keep_unknown_argv=True` to your `SourceFileGenerator`.
This will instruct it to store any unknown command line arguments into `sfg.context.argv`,
where you can then retrieve them from and pass on to your custom parser:

```{literalinclude} examples/guide_generator_scripts/custom_cmdline_args/kernels.py
```

Any SFG-specific arguments will already have been filtered out of this argument list.
As a consequence of the above, if the generator script is invoked with a typo in some SFG-specific argument,
which the `SourceFileGenerator` therefore does not recognize,
that argument will be passed on to your downstream parser instead.

:::{important}
If you do *not* pass on `sfg.context.argv` to a downstream parser, make sure that `keep_unknown_argv` is set to
`False` (which is the default), such that typos or illegal arguments will not be ignored.
:::
