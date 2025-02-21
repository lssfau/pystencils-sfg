# Installation and Setup

## Prequesites

To use pystencils-sfg, you will need at least Python 3.10.
You will also need the appropriate compilers for building the generated code,
such as
 - a modern C++ compiler (e.g. GCC, clang)
 - `nvcc` for CUDA or `hipcc` for HIP
 - Intel OneAPI or AdaptiveCpp for SYCL

Furthermore, an installation of clang-format for automatic code formatting is strongly recommended. 

## Install the Latest Development Revision

As pystencils-sfg is still unreleased, it can at this time only be obtained directly
from its Git repository.

Create a fresh [virtual environment](https://docs.python.org/3/library/venv.html) or activate
an existing one. Install both the pystencils 2.0 and pystencils-sfg development revisions from Git:

```{code-block} bash
pip install "git+https://i10git.cs.fau.de/pycodegen/pystencils.git@v2.0-dev"
pip install "git+https://i10git.cs.fau.de/pycodegen/pystencils-sfg.git"
```

````{caution}

*pystencils-sfg* is not compatible with the *pystencils 1.3.x* releases available from PyPI;
at the moment, you will still have to manually install the latest version of pystencils 2.0.
````

## Check your Installation

To verify that the SFG was successfully installed, execute the following command:

```{code-block} bash
sfg-cli version
```

You should see an output like `0.1a4+...`.

## Next Steps

Move on to [](#getting_started_guide) for a guide on how to author simple generator scripts.
