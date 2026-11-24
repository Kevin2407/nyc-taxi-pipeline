-- Exploración 4: datos de apoyo para interpretar las preguntas (b) y (f) de RESULTADOS.md.
-- Corre sobre el modelo (esquema modelo), después del pipeline.

-- (b) La hora 5 contra el resto: peso de los aeropuertos (JFK 132, LaGuardia 138) y distancia media.
select
    d.anio_mes,
    f.hora_subida = 5 as es_hora_5,
    round(100.0 * count(*) filter (where f.pu_zone_id in (132, 138) or f.do_zone_id in (132, 138))
          / count(*), 1) as pct_viajes_aeropuerto,
    round(avg(f.trip_distance) filter (where f.trip_distance > 0)::numeric, 2) as distancia_media
from modelo.fact_trips f
join modelo.dim_date d on f.fecha = d.fecha
group by 1, 2
order by 1, 2;

-- (f) Viajes aceptados de tipo de pago 0 (tarifa flexible) contra el resto.
select
    d.anio_mes,
    f.payment_type = 0 as es_tarifa_flexible,
    count(*) as viajes
from modelo.fact_trips f
join modelo.dim_date d on f.fecha = d.fecha
group by 1, 2
order by 1, 2;
