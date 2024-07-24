from .std_span import std_span_ref
from .std_mdspan import mdspan_ref
from .std_vector import std_vector_ref

span = std_span_ref
"""Create an ``std::span`` reference for a 1D pystencils field"""

mdspan = mdspan_ref
"""Create an ``std::mdspan`` reference for a pystencils field"""

vector = std_vector_ref
"""Create an ``std::vector`` reference for a 1D pystencils field"""
