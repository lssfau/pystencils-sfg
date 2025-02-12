from pystencilssfg import SourceFileGenerator

with SourceFileGenerator() as sfg:

    with sfg.namespace("outer"):
        sfg.code("constexpr int X = 13;")

        with sfg.namespace("inner"):
            sfg.code("constexpr int Y = 52;")

        sfg.code("constexpr int Z = 41;")

    with sfg.namespace("outer::second_inner"):
        sfg.code("constexpr int W = 91;")

    with sfg.namespace("outer::inner::innermost"):
        sfg.code("constexpr int V = 29;")

    sfg.code("constexpr int GLOBAL = 42;")
