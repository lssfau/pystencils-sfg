#pragma once

#include <cstdint>

{% for incl in public_includes %}
{{incl}}
{% endfor %}

#define RESTRICT __restrict__

{% if fq_namespace is not none %}
namespace {{fq_namespace}} {
{% endif %}

{% for function in functions %}
void {{ function.name }} ( {{ function | generate_function_parameter_list }} );
{% endfor %}

{% if fq_namespace is not none %}
} // namespace {{fq_namespace}}
{% endif %}