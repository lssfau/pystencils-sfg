import pytest
from os import path


@pytest.fixture(autouse=True)
def prepare_doctest_namespace(doctest_namespace):
    from pystencilssfg import SfgContext, SfgComposer
    from pystencilssfg import lang

    #   Place a composer object in the environment for doctests

    sfg = SfgComposer(SfgContext())
    doctest_namespace["sfg"] = sfg
    doctest_namespace["lang"] = lang


DATA_DIR = path.join(path.split(__file__)[0], "tests/data")


@pytest.fixture
def sample_config_module():
    return path.join(DATA_DIR, "project_config.py")
