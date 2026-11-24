-- Exploración 2: dónde se concentran los datos sucios, por tipo de pago.
-- 0 tarifa flexible, 1 tarjeta, 2 efectivo, 3 sin cargo, 4 disputa.
select
    mes_archivo,
    payment_type,
    count(*) as viajes,
    count(*) filter (where passenger_count is null) as pasajeros_nulo,
    count(*) filter (where passenger_count = 0) as pasajeros_cero,
    count(*) filter (where total_amount < 0) as total_negativo
from raw.yellow_trips
group by mes_archivo, payment_type
order by mes_archivo, payment_type;
