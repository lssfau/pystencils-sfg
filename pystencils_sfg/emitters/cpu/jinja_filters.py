from jinja2 import pass_context
from pystencils.astnodes import KernelFunction
from pystencils import Backend
from pystencils.backends import generate_c

@pass_context
def generate_kernel_definition(ctx, ast: KernelFunction):
    return generate_c(ast, dialect=Backend.C)

def add_filters_to_jinja(jinja_env):
    jinja_env.filters['generate_kernel_definition'] = generate_kernel_definition