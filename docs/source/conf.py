from pystencilssfg import __version__ as sfg_version
from packaging.version import Version

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "pystencils-sfg"
copyright = "2024, Frederik Hennig"
author = "Frederik Hennig"

parsed_version = Version(sfg_version)

version = ".".join([parsed_version.public])
release = sfg_version

html_title = f"pystencils-sfg v{version} Documentation"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
    "sphinx_design",
    "sphinx_copybutton"
]

templates_path = ["_templates"]
exclude_patterns = []
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}
master_doc = "index"
nitpicky = True


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
# html_static_path = ['_static']

#   Intersphinx

intersphinx_mapping = {
    "python": ("https://docs.python.org/3.8", None),
    "numpy": ("https://docs.scipy.org/doc/numpy/", None),
    "matplotlib": ("https://matplotlib.org/", None),
    "sympy": ("https://docs.sympy.org/latest/", None),
}


#   Autodoc options

autodoc_member_order = "bysource"
autodoc_typehints = "description"


#   Prepare code generation examples

def build_examples():
    import subprocess
    import os

    examples_dir = os.path.join("usage", "examples",)

    subprocess.run(["python", "build.py"], cwd=examples_dir).check_returncode()


print("Generating output of example scripts...")
build_examples()
