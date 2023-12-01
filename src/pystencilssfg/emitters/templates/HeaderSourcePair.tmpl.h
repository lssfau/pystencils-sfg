{{ prelude_comment | format_prelude_comment }}

#pragma once

#include <cstdint>

{% for incl in public_includes %}
{{incl}}
{% endfor %}

{% for definition in definitions %}
{{ definition }}
{% endfor %}

#define RESTRICT __restrict__

{% if fq_namespace is not none %}
namespace {{fq_namespace}} {
{% endif %}

{% for cls in classes %}
{{ cls | print_class_declaration }}
{% endfor %}

{% for function in functions %}
void {{ function.name }} ( {{ function | generate_function_parameter_list }} );
{% endfor %}

{% if fq_namespace is not none %}
} // namespace {{fq_namespace}}
{% endif %}