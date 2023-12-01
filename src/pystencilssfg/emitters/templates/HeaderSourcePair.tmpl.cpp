{{ prelude_comment | format_prelude_comment }}

#include "{{header_filename}}"

{% for incl in private_includes %}
{{incl}}
{% endfor %}

#define FUNC_PREFIX inline

{% if fq_namespace is not none %}
namespace {{fq_namespace}} {
{% endif %}

/*************************************************************************************
 *                                Kernels
*************************************************************************************/

{% for kns in kernel_namespaces %}
namespace {{ kns.name }} {

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
  {{ function | generate_function_body | indent(ctx.codestyle.indent_width) }}
}


{% endfor -%}

/*************************************************************************************
 *                                Class Methods
*************************************************************************************/

{% for cls in classes %}
{% for method in cls.methods() %}
void {{ cls.class_name }}::{{ method.name }} ( {{ method | generate_function_parameter_list }} ) { 
  {{ method | generate_function_body | indent(ctx.codestyle.indent_width) }}
}


{% endfor %}
{% endfor -%}

{% if fq_namespace is not none %}
} // namespace {{fq_namespace}}
{% endif %}
