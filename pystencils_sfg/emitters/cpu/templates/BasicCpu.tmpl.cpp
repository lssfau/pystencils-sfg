#include "{{basename}}.h"

#define FUNC_PREFIX inline

namespace {{root_namespace}} {

{% for kns in kernel_namespaces -%}
namespace {{ kns.name }}{

{% for ast in kns.asts -%}
{{ ast | generate_kernel_definition }}
{%- endfor %}

} // namespace {{ kns.name }}
{% endfor %}

} // namespace {{root_namespace}}
