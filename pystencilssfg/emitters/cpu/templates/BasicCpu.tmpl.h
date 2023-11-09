#pragma once

#define RESTRICT __restrict__

#include <cstdint>

{% for header in includes %}
#include {{header}}
{% endfor %}


namespace {{root_namespace}} {

{% for function in functions %}
void {{ function.name }} ( {{ function | generate_function_parameter_list }} );
{% endfor %}

} // namespace {{root_namespace}}
