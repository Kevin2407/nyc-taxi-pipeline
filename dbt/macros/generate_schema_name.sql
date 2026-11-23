{#
  Por defecto dbt antepone el esquema del perfil: "+schema: calidad" terminaría
  en "analitica_calidad". Con esta macro el esquema se llama exactamente como
  se configura (staging, calidad, marts).
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
