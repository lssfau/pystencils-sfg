from jinja2 import pass_context
from textwrap import indent

from pystencils.astnodes import KernelFunction
from pystencils import Backend
from pystencils.backends import generate_c

from pystencilssfg.source_components import SfgFunction, SfgClass
from .class_declaration import ClassDeclarationPrinter


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


@pass_context
def generate_function_body(ctx, func: SfgFunction):
    return func.get_code(ctx["ctx"])


@pass_context
def print_class_declaration(ctx, cls: SfgClass):
    return ClassDeclarationPrinter(ctx["ctx"]).print(cls)


def add_filters_to_jinja(jinja_env):
    jinja_env.filters["format_prelude_comment"] = format_prelude_comment
    jinja_env.filters["generate_kernel_definition"] = generate_kernel_definition
    jinja_env.filters[
        "generate_function_parameter_list"
    ] = generate_function_parameter_list
    jinja_env.filters["generate_function_body"] = generate_function_body

    jinja_env.filters["print_class_declaration"] = print_class_declaration
