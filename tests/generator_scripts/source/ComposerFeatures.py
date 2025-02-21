from pystencilssfg import SourceFileGenerator


with SourceFileGenerator() as sfg:

    sfg.function("factorial").params(sfg.var("n", "uint64")).returns(
        "uint64"
    ).inline().constexpr()(
        sfg.branch("n == 0")("return 1;")("return n * factorial(n - 1);")
    )

    q = sfg.var("q", "double")
    k = sfg.var("k", "uint64_t")
    x = sfg.var("x", "double")

    sfg.include("<cmath>")

    sfg.struct("Series")(
        sfg.method("geometric")
        .static()
        .attr("nodiscard")
        .params(q, k)
        .returns("double")(
            sfg.branch("k == 0")(
                "return 1.0;"
            )(
                "return Series::geometric(q, k - 1) + std::pow(q, k);"
            )
        )
    )

    sfg.struct("ConstexprMath")(
        sfg.method("abs").static().constexpr().inline()
        .params(x)
        .returns("double")
        (
            "if (x >= 0.0) return x; else return -x;"
        ),

        sfg.method("geometric")
        .static()
        .constexpr()
        .inline()
        .params(q, k)
        .returns("double")(
            sfg.branch("k == 0")(
                "return 1.0;"
            )(
                "return 1 + q * ConstexprMath::geometric(q, k - 1);"
            )
        )
    )

    with sfg.namespace("inheritance_test"):
        sfg.klass("Parent")(
            sfg.public(
                sfg.method("compute").returns("int").virtual().const()(
                    "return 24;"
                )
            )
        )

        sfg.klass("Child", bases=["public Parent"])(
            sfg.public(
                sfg.method("compute").returns("int").override().const()(
                    "return 31;"
                )
            )
        )
