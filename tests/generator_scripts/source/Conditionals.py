from pystencilssfg import SourceFileGenerator

with SourceFileGenerator() as sfg:
    sfg.namespace("gen")

    sfg.include("<iostream>")
    sfg.code(r"enum class Noodles { RIGATONI, RAMEN, SPAETZLE, SPAGHETTI };")

    noodle = sfg.var("noodle", sfg.cpptype("Noodles"))

    sfg.function("printOpinion")(
        sfg.switch(noodle)
        .case("Noodles::RAMEN")(
            'std::cout << "Great!" << std::endl;'
        )
        .case("Noodles::SPAETZLE")(
            'std::cout << "Amazing!" << std::endl;'
        )
        .default(
            'std::cout << "Okay, I guess..." << std::endl;'
        )
    )

    sfg.function("getRating", "int32")(
        sfg.switch(noodle, autobreak=False)
        .case("Noodles::RIGATONI")(
            "return 13;"
        )
        .case("Noodles::RAMEN")(
            "return 41;"
        )
        .case("Noodles::SPAETZLE")(
            "return 43;"
        )
        .case("Noodles::SPAGHETTI")(
            "return 15;"
        ),
        "return 0;"
    )

    sfg.function("isItalian", return_type="bool")(
        sfg.branch(
            sfg.expr("{0} == Noodles::RIGATONI || {0} == Noodles::SPAGHETTI", noodle)
        )(
            "return true;"
        )(
            "return false;"
        )
    )
