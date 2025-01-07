from pystencilssfg.lang import HeaderFile
import pytest


def test_parse_system():
    headerfile = HeaderFile.parse("<test>")
    assert str(headerfile) == "<test>" and headerfile.system_header


@pytest.mark.parametrize("header_string", ["test.hpp", '"test.hpp"'])
def test_parse_private(header_string):
    headerfile = HeaderFile.parse(header_string)
    assert str(headerfile) == "test.hpp" and not headerfile.system_header
