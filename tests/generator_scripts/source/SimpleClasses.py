from pystencilssfg import SourceFileGenerator

with SourceFileGenerator() as sfg:
    x_ = sfg.var("x_", "int64_t")
    y_ = sfg.var("y_", "int64_t")
    z_ = sfg.var("z_", "int64_t")

    x = sfg.var("x", "int64_t")
    y = sfg.var("y", "int64_t")
    z = sfg.var("z", "int64_t")

    sfg.klass("Point")(
        sfg.public(
            sfg.constructor(x, y, z).init(x_)(x).init(y_)(y).init(z_)(z),
            sfg.method("getX").returns("const int64_t").const().inline()(
                "return this->x_;"
            ),
        ),
        sfg.protected(x_, y_, z_),
    )

    sfg.klass("SpecialPoint", bases=["public Point"])(
        sfg.public(
            "using Point::Point;",
            sfg.method("getY").returns("const int64_t").const().inline()(
                "return this->y_;"
            ),
        )
    )
