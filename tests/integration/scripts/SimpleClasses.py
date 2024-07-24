from pystencilssfg import SourceFileGenerator

with SourceFileGenerator() as sfg:

    sfg.include("<cstdint>")

    sfg.klass("Point")(
        sfg.public(
            sfg.method("getX", returns="const int64_t &", const=True)(
                "return this->x;"
            )
        ),
        sfg.private(
            sfg.var("x", "int64_t"),
            sfg.var("y", "int64_t"),
            sfg.var("z", "int64_t")
        )
    )
