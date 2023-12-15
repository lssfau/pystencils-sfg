# Contributing

## Creating merge requests

Any contributions to this project must happen through GitLab merge requests to the main development
repository (currently [i10git.cs.fau.de/da15siwa/pystencils-sfg](https://i10git.cs.fau.de/da15siwa/pystencils-sfg)).
For a merge request to be accepted, it needs to both pass the continous integration pipeline and be approved by a project maintainer.

## Free Software

This project is free software under the GNU General Public Licence v3.
As such, any submission of contributions via merge requests is considered as agreement to this licence.

## Developing `pystencils-sfg`

### Fork and Clone

To work within the `pystencils-sfg` source tree, first create a *fork* of this repository on GitLab and create
a local clone of your fork.

### Set up your dev environment

`pystencils-sfg` uses [`pdm`](https://pdm-project.org) for managing a virtual development environment.
Install `pdm` through your system's package manager and run `pdm sync` in your cloned project directory.
It will set up a virtual environment in the subfolder `.venv`, installing all project dependencies into it.
The `pystencils-sfg` package itself is also installed in editable mode.
You can activate the virtual environment using `eval $(pdm venv activate)`.

### Code Style and Type Checking

To contribute, please adhere to the Python code style set by [PEP 8](https://peps.python.org/pep-0008/).
It is recommended that you use the [black](https://pypi.org/project/black/) formatter to format your source files.
Use flake8 (installed in the `pdm` virtual environment) to check your code style:

```shell
pdm run flake8 src/pystencilssfg
# or, if .venv is activated
flake8 src/pystencilssfg
```

Further, `pystencils-sfg` takes a rigorous approach to correct static typing.
All submitted code should contain type annotations ([PEP 484](https://peps.python.org/pep-0484/)) and must be
correctly statically typed.
To check types, we use [MyPy](https://www.mypy-lang.org/), which is automatically installed in the dev environment
and can be invoked as

```shell
pdm run mypy src/pystencilssfg
# or, if .venv is activated
mypy src/pystencilssfg
```

Both `flake8` and `mypy` are also run in the integration pipeline.
It is furthermore recommended to run both checkers as a git pre-commit hook.
Such a hook can be installed using the [`install_git_hooks.sh`](install_git_hooks.sh) script located at the project root.

