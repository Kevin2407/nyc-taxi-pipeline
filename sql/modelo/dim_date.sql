-- dim_date: una fila por día calendario con al menos un viaje en la capa curada.
select distinct
    fecha_subida as fecha,
    to_char(fecha_subida, 'YYYY-MM') as anio_mes,
    extract(year from fecha_subida)::int as anio,
    extract(month from fecha_subida)::int as mes,
    extract(day from fecha_subida)::int as dia,
    extract(isodow from fecha_subida)::int as dia_semana,
    trim(to_char(fecha_subida, 'Day')) as nombre_dia,
    extract(isodow from fecha_subida) >= 6 as es_fin_de_semana
from {{ ref('trips_curados') }}
