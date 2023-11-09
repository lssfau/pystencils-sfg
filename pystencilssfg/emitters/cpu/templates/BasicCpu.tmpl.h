#pragma once

#include <cstdint>

{% for incl in public_includes -%}
{{incl}}
{% endfor %}

#define RESTRICT __restrict__

namespace {{root_namespace}} {

{% for function in functions %}
void {{ function.name }} ( {{ function | generate_function_parameter_list }} );
{% endfor %}

} // namespace {{root_namespace}}
