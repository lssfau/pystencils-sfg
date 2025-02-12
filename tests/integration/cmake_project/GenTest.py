from pystencilssfg import SourceFileGenerator

with SourceFileGenerator() as sfg:
    sfg.namespace("gen")
    retval = 42 if sfg.context.project_info is None else sfg.context.project_info

    sfg.function("getValue", return_type="int")(
        f"return {retval};"
    )
