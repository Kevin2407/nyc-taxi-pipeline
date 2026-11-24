{# Macros de la parte de calidad. #}

{% macro columnas_contrato() %}
    {#- Las 20 columnas de contracts/yellow_schema.yaml, en su orden. -#}
    {{ return([
        'vendor_id', 'tpep_pickup_datetime', 'tpep_dropoff_datetime', 'passenger_count',
        'trip_distance', 'ratecode_id', 'store_and_fwd_flag', 'pu_location_id', 'do_location_id',
        'payment_type', 'fare_amount', 'extra', 'mta_tax', 'tip_amount', 'tolls_amount',
        'improvement_surcharge', 'total_amount', 'congestion_surcharge', 'airport_fee',
        'cbd_congestion_fee',
    ]) }}
{% endmacro %}


{% macro marcar_reglas(ids, condiciones) -%}
    {#-
      Arma la expresión que junta, separados por coma, los ids de las reglas que la fila viola.
      Ejemplo con ids = ['R04', 'R10']:
        concat_ws(',', case when <condición R04> then 'R04' end, case when <condición R10> then 'R10' end)
      concat_ws saltea los nulos, así que una fila sin violaciones da ''.
    -#}
    {%- if ids -%}
        concat_ws(','
        {%- for id in ids %},
            case when {{ condiciones[id] }} then '{{ id }}' end
        {%- endfor %})
    {%- else -%}
        ''
    {%- endif -%}
{%- endmacro %}
