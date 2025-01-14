# Contributing

## Creating merge requests

Any contributions to this project must happen through GitLab merge requests to the main development
repository ([i10git.cs.fau.de/pycodegen/pystencils-sfg](https://i10git.cs.fau.de/pycodegen/pystencils-sfg)).
For a merge request to be accepted, it needs to both pass the continous integration pipeline and be approved by a project maintainer.

## Free Software

This project is free software under the GNU General Public Licence v3.
As such, any submission of contributions via merge requests is considered as agreement to this licence.

## Developing `pystencils-sfg`

### Prequesites

To develop pystencils-sfg, you will need at least these packages:

 - Python 3.10
 - Git
 - A C++ compiler supporting at least C++20 (gcc >= 10, or clang >= 10)
 - GNU Make
 - CMake
 - Nox

Before continuing, make sure that the above packages are installed on your machine.

### Fork and Clone

To work within the `pystencils-sfg` source tree, first create a *fork* of this repository
and clone it to your workstation.

### Set up your dev environment

Create a virtual environment using either `venv` or `virtualenv` and install the pystencils-sfg source tree
into it using an editable install, e.g. by running the following commands in the `pystencils-sfg` project root directory:

```bash
python -m virtualenv .venv
source .venv/bin/activate
pip install -e .
```

If you have [nox](https://nox.thea.codes/en/stable/) installed, you can also set up your virtual environment
by running `nox --session dev_env`.

### Code Style and Type Checking

To contribute, please adhere to the Python code style set by [PEP 8](https://peps.python.org/pep-0008/).
For consistency, format all your source files using the [black](https://pypi.org/project/black/) formatter,
and check them regularily using the `flake8` linter through Nox:

```shell
nox --session lint
```

Further, `pystencils-sfg` is being fully type-checked using [MyPy](https://www.mypy-lang.org/).
All submitted code should contain type annotations ([PEP 484](https://peps.python.org/pep-0484/)) and must be
correctly statically typed.
Regularily check your code for type errors using

```shell
nox --session typecheck
```

Both `flake8` and `mypy` are also run in the integration pipeline.

### Test Your Code

We are working toward near-complete test coverage of the module source files.
When you add code, make sure to include test cases for both its desired
and exceptional behavior at the appropriate locations in the [tests](tests) directory.

Unit tests should be placed under a path and filename mirroring the location
of the API they are testing within the *pystencils-sfg* source tree.

In [tests/generator_scripts](tests/generator_scripts), a framework is provided to test entire generator scripts
for successful execution, correctness, and compilability of their output.
Read the documentation within [test_generator_scripts.py](tests/generator_scripts/test_generator_scripts.py)
for more information.

Run the test suite by calling it through Nox:

```shell
nox --session testsuite
```

This will also collect coverage information and produce a coverage report as a HTML site placed in the `htmlcov` folder.
