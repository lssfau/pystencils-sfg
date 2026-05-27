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
        .params(q, (k, "0"))
        .returns("double")(
            sfg.branch("k == 0")(
                "return 1.0;"
            )(
                "return Series::geometric(q, k - 1) + std::pow(q, k);"
            )
        )
    )

    sfg.struct("Math")(
        sfg.member_var("pi", "double").static().constexpr().init("3.1415962"),
        sfg.member_var("exp1f", "float").static().init("2.7f", out_of_line=True),

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
        .params(q, (k, "0"))
        .returns("double")(
            sfg.branch("k == 0")(
                "return 1.0;"
            )(
                "return 1 + q * Math::geometric(q, k - 1);"
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

    with sfg.namespace("ctor_test"):
        k = sfg.var("k", "int32")

        sfg.klass("StaticCounter")(
            sfg.public(
                sfg.constructor(k).body(
                    sfg.expr("StaticCounter::COUNTER += {};", k)
                ),
                sfg.method("getCounter").static().returns("int32")(
                    "return StaticCounter::COUNTER;"
                )
            ),
            sfg.private(
                sfg.member_var("COUNTER", "int32").static().init("0", out_of_line=True)
            )
        )

        #   Check if extra parameters raise
