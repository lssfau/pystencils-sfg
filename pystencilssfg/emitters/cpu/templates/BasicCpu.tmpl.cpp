#include "{{basename}}.h"

#define FUNC_PREFIX inline

namespace {{root_namespace}} {

/*************************************************************************************
 *                                Kernels
*************************************************************************************/

{% for kns in kernel_namespaces -%}
namespace {{ kns.name }}{

{% for ast in kns.asts %}
{{ ast | generate_kernel_definition }}
{% endfor %}

} // namespace {{ kns.name }}
{% endfor %}

/*************************************************************************************
 *                                Functions
*************************************************************************************/

{% for function in functions %}
void {{ function.name }} ( {{ function | generate_function_parameter_list }} ) { 
  {{ function | generate_function_body | indent(2) }}
}
{% endfor %}

} // namespace {{root_namespace}}
