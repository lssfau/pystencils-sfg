import pytest


@pytest.fixture(autouse=True)
def prepare_composer(doctest_namespace):
    from pystencilssfg import SfgContext, SfgComposer

    #   Place a composer object in the environment for doctests

    sfg = SfgComposer(SfgContext())
    doctest_namespace["sfg"] = sfg
