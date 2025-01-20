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
    "myst_nb",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosummary",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
    "sphinx_design",
    "sphinx_copybutton"
]

templates_path = ["_templates"]
exclude_patterns = []
master_doc = "index"
nitpicky = True


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_book_theme"
html_static_path = ['_static']
html_theme_options = {
   "logo": {
      "image_light": "_static/sfg-logo-light.svg",
      "image_dark": "_static/sfg-logo-dark.svg",
   }
}

#   Intersphinx

intersphinx_mapping = {
    "python": ("https://docs.python.org/3.8", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "sympy": ("https://docs.sympy.org/latest/", None),
    "pystencils": ("https://da15siwa.pages.i10git.cs.fau.de/dev-docs/pystencils-nbackend/", None),
}

#   References

#   Treat `single-quoted` code blocks as references to any
default_role = "any"

#   Autodoc options

autodoc_member_order = "bysource"
autodoc_typehints = "description"
# autodoc_class_signature = "separated"

#   Doctest Setup

doctest_global_setup = '''
from pystencilssfg import SfgContext, SfgComposer
sfg = SfgComposer(SfgContext())
'''


# -- Options for MyST / MyST-NB ----------------------------------------------

nb_execution_mode = "cache"  # do not execute notebooks by default

myst_enable_extensions = [
    "dollarmath",
    "colon_fence",
]

#   Prepare code generation examples

def build_examples():
    import subprocess
    import os

    examples_dir = os.path.join("usage", "examples",)

    subprocess.run(["python", "build.py"], cwd=examples_dir).check_returncode()


print("Generating output of example scripts...")
build_examples()
