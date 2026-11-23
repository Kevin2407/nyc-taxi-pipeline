-- (e) Viajes y tarifa media de los que empiezan o terminan en JFK o LaGuardia,
-- identificados por nombre de zona. Tarifa media sin los viajes con tarifa <= 0 (R09).
select
    d.anio_mes,
    count(*) as viajes,
    round((avg(f.fare_amount) filter (where f.fare_amount > 0))::numeric, 2) as tarifa_media
from {{ ref('fact_trips') }} f
join {{ ref('dim_date') }} d on f.fecha = d.fecha
join {{ ref('dim_zone') }} zo on f.pu_zone_id = zo.zone_id
join {{ ref('dim_zone') }} zd on f.do_zone_id = zd.zone_id
where d.anio_mes in ('{{ mes_asignado() }}', '{{ mes_anterior() }}')
  and (zo.zone in ('JFK Airport', 'LaGuardia Airport')
       or zd.zone in ('JFK Airport', 'LaGuardia Airport'))
group by d.anio_mes
order by d.anio_mes desc
