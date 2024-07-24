# Contributing

## Creating merge requests

Any contributions to this project must happen through GitLab merge requests to the main development
repository ([i10git.cs.fau.de/pycodegen/pystencils-sfg](https://i10git.cs.fau.de/pycodegen/pystencils-sfg)).
For a merge request to be accepted, it needs to both pass the continous integration pipeline and be approved by a project maintainer.

## Free Software

This project is free software under the GNU General Public Licence v3.
As such, any submission of contributions via merge requests is considered as agreement to this licence.

## Developing `pystencils-sfg`

### Fork and Clone

To work within the `pystencils-sfg` source tree, first create a *fork* of this repository on GitLab and create
a local clone of your fork.

### Set up your dev environment

Create a virtual environment using either `venv` or `virtualenv` and install the pystencils-sfg source tree
into it using an editable install, e.g. by running the following commands in the `pystencils-sfg` project root directory:

```bash
python -m virtualenv .venv
source .venv/bin/activate
pip install -e .
```

### Code Style and Type Checking

To contribute, please adhere to the Python code style set by [PEP 8](https://peps.python.org/pep-0008/).
For consistency, format all your source files using the [black](https://pypi.org/project/black/) formatter.
Use flake8 to check your code style:

```shell
flake8 src/pystencilssfg
```

Further, `pystencils-sfg` is being fully type-checked using [MyPy](https://www.mypy-lang.org/).
All submitted code should contain type annotations ([PEP 484](https://peps.python.org/pep-0484/)) and must be
correctly statically typed.
Before each commit, check your types by calling

```shell
mypy src/pystencilssfg
```

Both `flake8` and `mypy` are also run in the integration pipeline.
You can automate the code quality checks by running them via a git pre-commit hook.
Such a hook can be installed using the [`install_git_hooks.sh`](install_git_hooks.sh) script located at the project root.

