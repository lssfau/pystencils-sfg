from ..context import SfgContext

from ..visitors import CollectIncludes


def prepare_context(ctx: SfgContext):
    """Prepares a populated context for printing. Make sure to run this function on the
    [SfgContext][pystencilssfg.SfgContext] before passing it to a printer.

    Steps:
     - Collection of includes: All defined functions and classes are traversed to collect all required
       header includes
    """

    #   Collect all includes
    required_includes = CollectIncludes().visit(ctx)
    for incl in required_includes:
        ctx.add_include(incl)

    return ctx
