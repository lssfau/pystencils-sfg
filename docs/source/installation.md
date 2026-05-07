# Installation and Setup

## Prequesites

To use pystencils-sfg, you will need at least Python 3.10.
You will also need the appropriate compilers for building the generated code,
such as
 - a modern C++ compiler (e.g. GCC, clang)
 - `nvcc` for CUDA or `hipcc` for HIP
 - Intel OneAPI or AdaptiveCpp for SYCL

Furthermore, an installation of clang-format for automatic code formatting is strongly recommended. 

## Install pystencils-sfg

### From PyPI

Released versions of pystencils-sfg can be installed from PyPI using `pip`:

```bash
pip install pystencilssfg~=<version>
```

### From Git

You can also use `pip` to install a development revision of pystencils-sfg.
When doing so, we recommend pulling an appropriate development version of `pystencils` along with it.
Use the following commands (replace `<branch>` by the branches you want to check out):

```{code-block} bash
pip install "git+https://i10git.cs.fau.de/pycodegen/pystencils.git@<branch>"
pip install "git+https://i10git.cs.fau.de/pycodegen/pystencils-sfg.git@<branch>"
```

If you intend to develop `pystencils-sfg`, you can also clone the repository and perform an editable install:

```
git clone -b <branch> https://i10git.cs.fau.de/pycodegen/pystencils-sfg.git
pip install -e ./pystencils-sfg
```

## Check your Installation

To verify that the SFG was successfully installed, execute the following command:

```{code-block} bash
sfg-cli version
```

## Next Steps

Move on to [](#getting_started_guide) for a guide on how to author simple generator scripts.
