import pytest

from pystencilssfg import SfgException


def test_extraneous_args(sfg):
    x = sfg.var("x", "int32")
    y = sfg.var("y", "int32")
    z = sfg.var("z", "int32")

    with pytest.raises(SfgException):
        sfg.function("fail").params(x, y).returns("int32")(
            sfg.expr("return {} + {};", x, z)
        )

    with pytest.raises(SfgException):
        sfg.klass("test")(
            sfg.method("fail")
            .params(x)
            .returns("int32")(
                sfg.expr("return {} + {};", x, z)
            )
        )
