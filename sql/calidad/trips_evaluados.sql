{#
  Parte 3 de la consigna: aplica las reglas de calidad a cada fila.

  - La CONDICIÓN de cada regla está acá abajo, en SQL: es verdadera cuando la fila VIOLA la regla.
  - La SEVERIDAD (rechazo o advertencia), la descripción y la justificación están en
    contracts/reglas_calidad.csv (un seed de dbt). dbt lee ese seed antes de armar el SQL: cambiar una
    severidad es editar una celda del CSV, no este archivo.
  - Si una condición da nulo porque falta un dato, CASE WHEN no la marca: la fila
    no viola la regla (no podemos afirmar que esté mal).

  Resultado: todas las filas, con dos columnas nuevas:
    reglas_violadas  ids de las reglas de RECHAZO que viola, separados por coma ('' si ninguna)
    flags            ids de las reglas de ADVERTENCIA que viola ('' si ninguna)
#}

-- depends_on: {{ ref('reglas_calidad') }}

{% set condiciones = {
    'R01': "to_char(tpep_pickup_datetime, 'YYYY-MM') <> mes_archivo",
    'R02': "tpep_dropoff_datetime <= tpep_pickup_datetime",
    'R03': "trip_distance <= 0",
    'R04': "trip_distance > " ~ var('distancia_maxima_millas'),
    'R05': "total_amount < 0",
    'R06': "passenger_count is null or passenger_count = 0",
    'R07': "sin_zona_origen or sin_zona_destino",
    'R08': "copia > 1",
    'R09': "fare_amount <= 0",
    'R10': "tpep_dropoff_datetime > tpep_pickup_datetime and trip_distance / (extract(epoch from tpep_dropoff_datetime - tpep_pickup_datetime) / 3600.0) > " ~ var('velocidad_maxima_mph'),
    'R11': "pu_location_id in (264, 265) or do_location_id in (264, 265)",
} %}

{# Las 20 columnas del contrato: dos filas son duplicado exacto si coinciden en todas. #}
{% set columnas = columnas_contrato() %}

{# Lee el seed y reparte los ids según su severidad. #}
{% set rechazo = [] %}
{% set advertencia = [] %}
{% if execute %}
    {% set reglas = run_query('select id, severidad from ' ~ ref('reglas_calidad') ~ ' order by id') %}
    {% for fila in reglas.rows %}
        {% if fila['id'] not in condiciones %}
            {{ exceptions.raise_compiler_error('La regla ' ~ fila['id'] ~ ' está en el seed pero no tiene condición en trips_evaluados.sql') }}
        {% elif fila['severidad'] == 'rechazo' %}
            {% do rechazo.append(fila['id']) %}
        {% elif fila['severidad'] == 'advertencia' %}
            {% do advertencia.append(fila['id']) %}
        {% else %}
            {{ exceptions.raise_compiler_error('Severidad desconocida en ' ~ fila['id'] ~ ': ' ~ fila['severidad']) }}
        {% endif %}
    {% endfor %}
    {% for id in condiciones %}
        {% if id not in rechazo and id not in advertencia %}
            {{ exceptions.raise_compiler_error('La regla ' ~ id ~ ' tiene condición pero no está en el seed reglas_calidad.csv') }}
        {% endif %}
    {% endfor %}
{% endif %}

with viajes as (
    select * from {{ ref('stg_yellow_trips') }}
),

zonas as (
    select location_id from {{ ref('stg_zonas') }}
),

con_datos_auxiliares as (
    select
        v.*,
        -- R07: la zona no existe en la tabla de zonas (un id nulo tampoco existe)
        zo.location_id is null as sin_zona_origen,
        zd.location_id is null as sin_zona_destino,
        -- R08: numera las filas idénticas dentro del mismo archivo; la 1 se conserva
        row_number() over (
            partition by {{ columnas | join(', ') }}, v.archivo_origen
        ) as copia
    from viajes v
    left join zonas zo on v.pu_location_id = zo.location_id
    left join zonas zd on v.do_location_id = zd.location_id
)

select
    {{ columnas | join(',\n    ') }},
    archivo_origen,
    mes_archivo,
    {{ marcar_reglas(rechazo, condiciones) }} as reglas_violadas,
    {{ marcar_reglas(advertencia, condiciones) }} as flags
from con_datos_auxiliares
