# Generator Script Test Suite

This directory contains the generator script test suite of pystencils-sfg.
Here, the code generation pipeline of the SFG is tested in full by running
and evaluating the output of generator scripts.
This has proven much more effective than trying to construct fine-grained
unit tests for the `composer`, `ir` and `emission` modules.

## Structure

The `pystencils-sfg/tests/generator-scripts` directory contains these subfolders and files:
 - `deps`: Dependencies of the test suite, e.g. std::mdspan
 - `source`: Generator scripts, their configuration and test harnesses
 - `index.yaml`: Test suite index
 - `test_generator_scripts.py`: Actual test suite code, run by pytest

## Registering Tests

A generator script test comprises at least a generator script `<name>.py` in the `source` directory,
and an associated entry in `index.yaml`.
That entry may define various options for the testing run of that script.
A test may optionally define a C++ harness program called `<name>.harness.cpp` in the `source` directory,
against which the generated code will be tested.

### Creating a New Test

At its top level, the test index file `index.yaml` is a dictionary mapping test names to their parameters.
After creating the `<name>.py` generator script, we register it by adding an empty entry:

```yaml
# somewhere in index.yaml

<name>:
    # params (might be empty)
```

This will allow the test suite to discover `<name>.py` and add an associated test to its `pytest` test set.
The test can be parametrized using the parameters listed in the parameter reference below.

### Test Execution Flow

The above empty test definition already leads to the following execution flow:
 - The generator script is executed and its output placed in a temporary directory.
   If the script fails, so does the test.
 - The set of output files is checked against the expected file set.
   By default, scripts are expected to emit one `.hpp` file and one `.cpp` file,
   but the expected files can be affected with test parameters as explained below.
 - If any generated files are detected as 'compilable' from their extensions (candidates are `.cpp`, `.cxx`, and`.c++`).
   the test suite will attempt to compile them using default settings
   (currently `g++ -std=c++20`, with the `<experimental/mdspan>` header in scope).
   If compilation fails, the test fails.
 - If a test harness (`<name>.harness.cpp`) is found in the `source` folder, it will be compiled and linked as an executable
   against the generated files.
   The harness executable is then executed.
   If compilation fails or execution yields a return code other than `0`, the test fails.

If all steps run without errors, the test succeeds.

### Writing a Test Harness

The most important requirement placed on our code generator is that it produces
functionally correct code that adheres exactly to its input specification.
For one, all generated code must be compilable using an appropriate compiler,
so compiling it (with strict treatment of warnings) as part of the test is a sure way of
checking its syntactical correctness.
Its semantical correctness can be further ensured by providing a C++ test harness.
This test harness can check the semantics of the generated code both statically
(using compile-time assertions, combined with concepts or type traits)
and dynamically (by executing the generated code and checking its output).

Each generator script registered at the test suite can have one test harness named `<name>.harness.cpp`
in the `source` folder. That test harness should `#include` any generated header files
(the test suite ensures the generated files are on the compiler's include path).

Since it will be compiled to an executable, the test harness must also define a `main` function
which should call any dynamic functional tests of the generated code.
If any dynamic test fails, the harness application must terminate with a nonzero error code.

## Test Index (`index.yaml`) Parameter Reference

Each entry in `index.yaml` must be a dictionary.
The test suite parses the following (groups of) parameters:

#### `sfg-args`

SFG-related command-line parameters passed to the generator script.
These may be:
- `header-only` (`true` or `false`): Enable or disable header-only code generation.
  If `true`, the set of expected output files is reduced to `{".hpp"}`.
- `file-extensions`: List of file extensions for the output files of the generator script.
  If specified, these are taken as the expected output files by the test suite.
- `config-module`: Path to a config module, relative to `source/`.
  The Python file referred to by this option will be passed as a configuration module to the generator script.

#### `extra-args`
List of additional command line parameters passed to the script.

#### `expected-output`

List of file extensions that are expected to be produced by the generator script.
Overrides any other source of expected file extensions;
use this if file extensions are determined by inline configuration or the configuration module.

#### `expect-failure`

Boolean indicating whether the script is expected to fail.
If set to `True`, the test fails if the script runs successfully.

#### `expect-code`

Dictionary mapping file extensions to a list of string patterns
that are expected to be generated in the respective files.
These patterns may be:
- A plain string: In this case, that string must be contained verbatim in the generated code
- A dictionary defining at least the `regex` key containing a regular expressions,
  and some options affecting its matching.

**Example: Plain String** 
This example requires that the generated `hpp` file contains the inclusion of `iostream` verbatim:

```yaml
MyTest:
  expect-code:
    hpp:
      - "#include <iostream>"
```

**Example: Regular Expression**
This example requires a type alias for an `std::mdspan` instance be defined in the header file,
but does not care about the exact extents, or number of spaces used inside the template parameter list:

```yaml
MyTest:
  expect-code:
    hpp:
      - regex: using\sfield_t\s=\sstd::mdspan<\s*float,\s*std::extents<.*>\s*>
```

In the regex example, the pattern is a dictionary with the single key `regex`.
Regex matching can be configured by adding additional keys:
- `count`: How often the regex should match; default is `1`
- `strip-whitespace`: Set to `true` to have the test suite remove any whitespace from the regex string.
  Use this if you want to break your long regular expression across several lines. Default is `false`.

**Example: Multiline Regex**
This example is the same as above, but using folded block style (see [yaml-multiline.info](https://yaml-multiline.info/))
to line-break the regex:

```yaml
MyTest:
  expect-code:
    hpp:
      - regex: >-
            using\sfield_t\s=
            \sstd::mdspan<\s*
                float,\s*
                std::extents<.*>
            \s*>
      - strip-whitespace: true
```

#### `compile`

Options affecting compilation of the generated files and the test harness.
Possible options are:
- `cxx`: Executable of the C++ compiler; default is `g++`
- `cxx-flags`: List of arguments to the C++ compiler; default is `["-std=c++20", "-Wall", "-Werror"]`
- `link-flags`: List of arguments for the linker; default is `[]`
- `skip-if-not-found`: If set to `true` and the compiler specified in `cxx` cannot be found,
  skip compilation and harness execution. Otherwise, fail the test.

## Dependencies

The `deps` folder includes any vendored dependencies required by generated code.
At the moment, this includes the reference implementation of `std::mdspan`
provided by the Kokkos group [here](https://github.com/kokkos/mdspan).
