
(how_to_generator_scripts_config)=
# Generator Script Configuration and Command-Line Interface

There are several ways to affect the behavior and output of a generator script.
For one, the `SourceFileGenerator` itself may be configured from the combination of three
different configuration sources:

- **Inline Configuration:** The generator script may set up an {any}`SfgConfig` object,
  which is passed to the `SourceFileGenerator` at its creation; see [Inline Configuration](#inline_config)
- **Command-Line Options:** The `SourceFileGenerator` parses the command line arguments of
  the generator script to set some of its configuration options; see [Command-Line Options](#cmdline_options)
- **Project Configuration:** When embedded into a larger project, using a build system such as CMake, generator scripts
  may be configured globally within that project by the use of a *configuration module*.
  Settings specified inside that configuration module are always overridden by the two other configuration sources listed above.
  For details on configuration modules, refer to the guide on [Project and Build System Integration](#guide_project_integration).

(inline_config)=
## Inline Configuration

To configure the source file generator within your generator script, import the {any}`SfgConfig` from `pystencilssfg`.
You may then set up the configuration object before passing it to the `SourceFileGenerator` constructor.
To illustrate, the following snippet alters the code indentation width and changes the output directory
of the generator script to `gen_src`:

```{literalinclude} examples/guide_generator_scripts/inline_config/kernels.py
```

For a selection of common configuration options, see [below](#config_options).
The inline configuration will override any values set by the [project configuration](#config_module)
and must not conflict with any [command line arguments](#custom_cli_args).

(config_options)=
## Configuration Options

Here is a selection of common configuration options to be set in the [inline configuration](#inline_config) or
[project configuration](#config_module).

### Output Options

The file extensions of the generated files can be modified through
{any}`cfg.extensions.header <FileExtensions.header>`
and {any}`cfg.extensions.impl <FileExtensions.impl>`;
and the output directory of the code generator can be set through {any}`cfg.output_directory <SfgConfig.output_directory>`.
The [header-only mode](#header_only_mode) can be enabled using {any}`cfg.header_only <SfgConfig.header_only>`.

:::{danger}

When running generator scripts through [CMake](#cmake_integration), the file extensions,
output directory, and header-only mode settings will be managed fully by the pystencils-sfg
CMake module and the (optional) project configuration module.
They should therefore not be set in the inline configuration,
as this will likely lead to errors being raised during code generation.
:::

### Outer Namespace

To specify the outer namespace to which all generated code should be emitted,
set {any}`cfg.outer_namespace <SfgConfig.outer_namespace>`.

### Code Style and Formatting

Pystencils-sfg gives you some options to affect its output code style.
These are controlled by the options in the {any}`cfg.code_style <CodeStyle>` category.

Furthermore, pystencils-sfg uses `clang-format` to beautify generated code.
The behaviour of the clang-format integration is managed by the
the {any}`cfg.clang_format <ClangFormatOptions>` category,
where you can set options to skip or enforce formatting,
or change the formatter binary.
To set the code style used by `clang-format` either create a `.clang-format` file
in any of the parent folders of your generator script,
or modify the {any}`cfg.clang_format.code_style <ClangFormatOptions.code_style>` option.

:::{seealso}
[Clang-Format Style Options](https://clang.llvm.org/docs/ClangFormatStyleOptions.html)
:::

Clang-format will, by default, sort `#include` statements alphabetically and separate
local and system header includes.
To override this, you can set a custom sorting key for `#include` sorting via
{any}`cfg.code_style.includes_sorting_key <CodeStyle.includes_sorting_key>`.

(cmdline_options)=
## Command-Line Options

The `SourceFileGenerator` consumes a number of command-line parameters that may be passed to the script
on invocation. These include:

- `--sfg-output-dir <path>`: Set the output directory of the generator script. This corresponds to {any}`SfgConfig.output_directory`.
- `--sfg-file-extensions <exts>`: Set the file extensions used for the generated files;
  `exts` must be a comma-separated list not containing any spaces. Corresponds to {any}`SfgConfig.extensions`.
- `[--no]--sfg-header-only`: Enable or disable header-only code generation. Corresponds to {any}`SfgConfig.header_only`.

If any configuration option is set to conflicting values on the command line and in the inline configuration,
the generator script will terminate with an error.

You may examine the full set of possible command line parameters by invoking a generator script
with the `--help` flag:

```bash
$ python kernels.py --help
```

(header_only_mode)=
## Header-Only Mode

When the header-only output mode is enabled,
the code generator will emit only a header file and no separate implementation file.
In this case, the composer will automatically place all function, method,
and kernel definitions in the header file.

Header-only code generation can be enabled by setting the `--header-only` command-line flag
or the {any}`SfgConfig.header_only` configuration option.

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
