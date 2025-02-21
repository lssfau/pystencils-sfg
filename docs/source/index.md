# The pystencils Source File Generator


[![pipeline](https://i10git.cs.fau.de/pycodegen/pystencils-sfg/badges/master/pipeline.svg)](https://i10git.cs.fau.de/pycodegen-/pystencils-sfg/commits/master)
[![coverage](https://i10git.cs.fau.de/pycodegen/pystencils-sfg/badges/master/coverage.svg)](https://i10git.cs.fau.de/pycodegen-/pystencils-sfg/commits/master)
[![licence](https://img.shields.io/gitlab/license/pycodegen%2Fpystencils-sfg?gitlab_url=https%3A%2F%2Fi10git.cs.fau.de)](https://i10git.cs.fau.de/pycodegen/pystencils-sfg/-/blob/master/LICENSE)

*A bridge over the semantic gap between [pystencils](https://pypi.org/project/pystencils/) and C++ HPC frameworks.*

The pystencils Source File Generator is a code generation tool that allows you to
declaratively describe and automatically generate C++ code using its Python API.
It is part of the wider [pycodegen][pycodegen] family of packages for scientific code generation.

The primary purpose of pystencils-sfg is to embed the [pystencils][pystencils] code generator for
high-performance stencil computations into C++ HPC applications and frameworks of all scales.
Its features include:

 - Exporting pystencils kernels to C++ source files for use in larger projects
 - Mapping of symbolic pystencils fields onto a wide variety of n-dimensional array data structures
 - Orchestration of code generation as part of a Makefile or CMake project
 - Declarative description of C++ code structure including functions and classes using the versatile composer API
 - Reflection of C++ APIs in the code generator, including automatic tracking of variables and `#include`s


## Table of Contents

```{toctree}
:maxdepth: 1

installation
getting_started
```

```{toctree}
:maxdepth: 1
:caption: User Guide

usage/how_to_composer
usage/api_modelling
usage/config_and_cli
usage/project_integration
usage/tips_n_tricks
```


```{toctree}
:maxdepth: 1
:caption: API Reference

api/generation
api/composer
api/lang
api/ir
api/errors
```

[pycodegen]: https://pycodegen.pages.i10git.cs.fau.de
[pystencils]: https://pycodegen.pages.i10git.cs.fau.de/docs/pystencils/2.0dev
