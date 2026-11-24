{# Mes asignado y mes de comparación, para las preguntas de negocio. #}

{% macro mes_asignado() %}
    {#- Se toma de la variable "mes" (dbt build --vars '{mes: 2025-04}') o, si no se pasa,
        de la variable de entorno MES del docker-compose. -#}
    {{ return(var('mes', env_var('MES', '2025-03'))) }}
{% endmacro %}

{% macro mes_anterior() %}
    {#- El mismo mes del año anterior: 2025-03 -> 2024-03. -#}
    {%- set mes = mes_asignado() -%}
    {{ return((mes[:4] | int - 1) ~ mes[4:]) }}
{% endmacro %}
