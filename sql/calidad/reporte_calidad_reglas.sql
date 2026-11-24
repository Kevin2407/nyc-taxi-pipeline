-- Cantidad de filas que viola cada regla, por mes. Una fila puede violar varias reglas,
-- así que estos números no se suman. Las reglas sin casos aparecen con 0.
with marcas as (
    select mes_archivo, unnest(string_to_array(reglas_violadas, ',')) as regla
    from {{ ref('trips_evaluados') }}
    where reglas_violadas <> ''
    union all
    select mes_archivo, unnest(string_to_array(flags, ',')) as regla
    from {{ ref('trips_evaluados') }}
    where flags <> ''
),
conteos as (
    select mes_archivo, regla, count(*) as filas
    from marcas
    group by mes_archivo, regla
),
meses as (
    select distinct mes_archivo from {{ ref('stg_yellow_trips') }}
)
select
    m.mes_archivo,
    r.id as regla,
    r.nombre,
    r.severidad,
    coalesce(c.filas, 0) as filas
from meses m
cross join {{ ref('reglas_calidad') }} r
left join conteos c on c.mes_archivo = m.mes_archivo and c.regla = r.id
order by m.mes_archivo, r.id
