from pystencilssfg import SourceFileGenerator

with SourceFileGenerator() as sfg:
    sfg.include("<iostream>")

    sfg.function("myFunction")(
        r'std::cout << "mdspans!\n";'
    )
