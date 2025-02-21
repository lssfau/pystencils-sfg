from __future__ import annotations

from typing import Sequence
import nox

nox.options.sessions = ["lint", "typecheck", "testsuite"]


def add_pystencils_git(session: nox.Session):
    """Clone the pystencils 2.0 development branch and install it in the current session"""
    cache_dir = session.cache_dir

    pystencils_dir = cache_dir / "pystencils"
    if pystencils_dir.exists():
        with session.chdir(pystencils_dir):
            session.run_install("git", "pull", external=True)
    else:
        session.run_install(
            "git",
            "clone",
            "--branch",
            "v2.0-dev",
            "--single-branch",
            "https://i10git.cs.fau.de/pycodegen/pystencils.git",
            pystencils_dir,
            external=True,
        )
    session.install("-e", str(pystencils_dir))


def editable_install(session: nox.Session, opts: Sequence[str] = ()):
    add_pystencils_git(session)
    if opts:
        opts_str = "[" + ",".join(opts) + "]"
    else:
        opts_str = ""
    session.install("-e", f".{opts_str}")


@nox.session(python="3.10", tags=["qa", "code-quality"])
def lint(session: nox.Session):
    """Lint code using flake8"""

    session.install("flake8")
    session.run("flake8", "src/pystencilssfg")


@nox.session(python="3.10", tags=["qa", "code-quality"])
def typecheck(session: nox.Session):
    """Run MyPy for static type checking"""
    editable_install(session)
    session.install("mypy")
    session.run("mypy", "src/pystencilssfg")


@nox.session(python=["3.10", "3.11", "3.12", "3.13"], tags=["tests"])
def testsuite(session: nox.Session):
    """Run the testsuite and measure coverage."""
    editable_install(session, ["testsuite"])
    session.run(
        "pytest",
        "-v",
        "--cov=src/pystencilssfg",
        "--cov-report=term",
        "--cov-config=pyproject.toml",
    )
    session.run("coverage", "html")
    session.run("coverage", "xml")


@nox.session(python=["3.10"], tags=["docs"])
def docs(session: nox.Session):
    """Build the documentation pages"""
    editable_install(session, ["docs"])

    env = {}

    session_args = session.posargs
    if "--fail-on-warnings" in session_args:
        env["SPHINXOPTS"] = "-W --keep-going"

    session.chdir("docs")

    if "--clean" in session_args:
        session.run("make", "clean", external=True)

    session.run("make", "html", external=True)


@nox.session()
def dev_env(session: nox.Session):
    """Set up the development environment at .venv"""

    session.install("virtualenv")
    session.run("virtualenv", ".venv", "--prompt", "pystencils-sfg")
    session.run(
        ".venv/bin/pip",
        "install",
        "git+https://i10git.cs.fau.de/pycodegen/pystencils.git@v2.0-dev",
        external=True,
    )
    session.run(".venv/bin/pip", "install", "-e", ".[dev]", external=True)
