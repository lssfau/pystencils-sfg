import pytest
from os import path


DATA_DIR = path.join(path.split(__file__)[0], "tests/data")


@pytest.fixture
def sample_config_module():
    return path.join(DATA_DIR, "project_config.py")


@pytest.fixture
def sfg():
    from pystencilssfg import SfgContext, SfgComposer
    from pystencilssfg.ir import SfgSourceFile, SfgSourceFileType

    return SfgComposer(
        SfgContext(
            header_file=SfgSourceFile("", SfgSourceFileType.HEADER),
            impl_file=SfgSourceFile("", SfgSourceFileType.TRANSLATION_UNIT),
        )
    )


@pytest.fixture(autouse=True)
def prepare_doctest_namespace(doctest_namespace, sfg):
    from pystencilssfg import lang

    doctest_namespace["sfg"] = sfg
    doctest_namespace["lang"] = lang
