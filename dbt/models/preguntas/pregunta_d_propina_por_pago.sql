-- (d) Propina promedio como porcentaje de la tarifa, por tipo de pago, en los dos meses.
-- propina_pct es nula cuando la tarifa es <= 0 (regla R09); avg() ignora esos viajes.
-- El efectivo da 0 % y no es interpretable: la propina en efectivo no queda registrada.
select
    d.anio_mes,
    f.payment_type,
    case f.payment_type
        when 0 then 'Tarifa flexible'
        when 1 then 'Tarjeta de crédito'
        when 2 then 'Efectivo'
        when 3 then 'Sin cargo'
        when 4 then 'Disputa'
        when 5 then 'Desconocido'
        when 6 then 'Viaje anulado'
    end as forma_pago,
    count(*) as viajes,
    round(avg(f.propina_pct)::numeric, 2) as propina_promedio_pct
from {{ ref('fact_trips') }} f
join {{ ref('dim_date') }} d on f.fecha = d.fecha
where d.anio_mes in ('{{ mes_asignado() }}', '{{ mes_anterior() }}')
group by d.anio_mes, f.payment_type
order by d.anio_mes desc, f.payment_type
