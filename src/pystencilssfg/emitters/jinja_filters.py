from jinja2 import pass_context
from textwrap import indent

from pystencils.astnodes import KernelFunction
from pystencils import Backend
from pystencils.backends import generate_c

from pystencilssfg.source_components import SfgFunction


def format_prelude_comment(prelude_comment: str):
    if not prelude_comment:
        return ""

    return "/*\n" + indent(prelude_comment, "* ", predicate=lambda _: True) + "*/\n"


@pass_context
def generate_kernel_definition(ctx, ast: KernelFunction):
    return generate_c(ast, dialect=Backend.C)


@pass_context
def generate_function_parameter_list(ctx, func: SfgFunction):
    params = sorted(list(func.parameters), key=lambda p: p.name)
    return ", ".join(f"{param.dtype} {param.name}" for param in params)


def generate_function_body(func: SfgFunction):
    return func.get_code()


def add_filters_to_jinja(jinja_env):
    jinja_env.filters['format_prelude_comment'] = format_prelude_comment
    jinja_env.filters['generate_kernel_definition'] = generate_kernel_definition
    jinja_env.filters['generate_function_parameter_list'] = generate_function_parameter_list
    jinja_env.filters['generate_function_body'] = generate_function_body
