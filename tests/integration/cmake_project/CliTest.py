from pystencilssfg import SourceFileGenerator

with SourceFileGenerator(keep_unknown_argv=True) as sfg:
    sfg.include("<string>")
    for i, arg in enumerate(sfg.context.argv):
        sfg.code(f"constexpr std::string arg{i} = \"{arg}\";")
