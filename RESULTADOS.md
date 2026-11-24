# Resultados

Mes asignado: **marzo 2025**, comparado contra **marzo 2024**.

Cada pregunta es un modelo de dbt (un archivo en `sql/preguntas/`) que se guarda como tabla en el esquema `preguntas` de Postgres. Se construyen con el pipeline completo (`make all MES=2025-03`) y se muestran con:

```bash
make respuestas MES=2025-03
# o: docker compose run --rm herramientas python -m src.modelo --mes 2025-03 --solo-respuestas
```

Todas las consultas corren sobre el modelo estrella (`modelo.fact_trips`, `modelo.dim_zone`, `modelo.dim_date`, `modelo.agg_zone_hour`), que contiene solo los viajes aceptados por las reglas de calidad: 3.535.924 de marzo 2024 y 4.053.200 de marzo 2025. En el SQL, `{{ ref('...') }}` es la forma de dbt de nombrar otra tabla del proyecto, y `{{ mes_asignado() }}` / `{{ mes_anterior() }}` son el mes de la corrida y el mismo mes del año anterior. Criterios comunes:

- La **tarifa media** se calcula sin los viajes con tarifa <= 0 (regla R09), porque esa tarifa no es válida.
- Los rankings por zona excluyen las zonas 264 (Unknown) y 265 (Outside of NYC) (regla R11).

## Pregunta a

**Las 10 zonas de origen con más viajes y su variación contra marzo 2024.**

| Zona de origen | Barrio | Viajes 2025-03 | Viajes 2024-03 | Variación |
| --- | --- | --- | --- | --- |
| Midtown Center | Manhattan | 177.779 | 161.246 | +10,3 % |
| Upper East Side South | Manhattan | 167.141 | 153.947 | +8,6 % |
| JFK Airport | Queens | 151.140 | 152.145 | −0,7 % |
| Upper East Side North | Manhattan | 150.093 | 144.799 | +3,7 % |
| Times Sq/Theatre District | Manhattan | 132.651 | 120.857 | +9,8 % |
| Penn Station/Madison Sq West | Manhattan | 129.525 | 113.202 | +14,4 % |
| Midtown East | Manhattan | 125.943 | 122.378 | +2,9 % |
| Lincoln Square East | Manhattan | 114.814 | 113.603 | +1,1 % |
| Union Sq | Manhattan | 112.180 | 96.367 | +16,4 % |
| East Village | Manhattan | 108.502 | 92.276 | +17,6 % |

**Interpretación:** nueve de las diez zonas son de Manhattan y crecieron hasta un 17,6 %; la única que cae es JFK, lo que sugiere que el aumento de viajes es urbano y no de aeropuerto.

Consulta: `sql/preguntas/pregunta_a_top10_zonas_origen.sql` (tabla `preguntas.pregunta_a_top10_zonas_origen`)

```sql
-- (a) Las 10 zonas de origen con más viajes en el mes y su variación contra el mismo mes de 2024.
-- Se excluyen las zonas 264 (Unknown) y 265 (Outside of NYC): no son un lugar (regla R11).
with viajes_por_zona as (
    select
        a.pu_zone_id,
        sum(a.viajes) filter (where d.anio_mes = '{{ mes_asignado() }}') as viajes_mes,
        sum(a.viajes) filter (where d.anio_mes = '{{ mes_anterior() }}') as viajes_mes_anterior
    from {{ ref('agg_zone_hour') }} a
    join {{ ref('dim_date') }} d on a.fecha = d.fecha
    where a.pu_zone_id not in (264, 265)
    group by a.pu_zone_id
)
select
    z.zone as zona_origen,
    z.borough as barrio,
    v.viajes_mes,
    v.viajes_mes_anterior,
    round(100.0 * (v.viajes_mes - v.viajes_mes_anterior) / v.viajes_mes_anterior, 1) as variacion_pct
from viajes_por_zona v
join {{ ref('dim_zone') }} z on v.pu_zone_id = z.zone_id
order by v.viajes_mes desc nulls last
limit 10
```

## Pregunta b

**La hora del día con mayor ingreso promedio por viaje.**

| Mes | Hora | Viajes en esa hora | Ingreso promedio por viaje |
| --- | --- | --- | --- |
| 2025-03 | 5 (5:00 a 5:59) | 32.592 | 33,75 USD |
| 2024-03 | 5 (5:00 a 5:59) | 22.684 | 35,19 USD |

**Interpretación:** a las 5 de la mañana hay pocos viajes pero largos: el 18 a 21 % toca un aeropuerto (contra 8 a 9 % en el resto del día) y la distancia media es de 5,7 millas contra 3,3 (datos de `exploracion/04_resultados.sql`).

El ingreso es `total_amount`. El promedio se calcula como ingreso total / viajes de la hora, a partir de `agg_zone_hour`. Postgres no tiene `QUALIFY`: `DISTINCT ON` se queda con la hora de mayor ingreso de cada mes.

Consulta: `sql/preguntas/pregunta_b_hora_mayor_ingreso.sql` (tabla `preguntas.pregunta_b_hora_mayor_ingreso`)

```sql
-- (b) La hora del día con mayor ingreso promedio por viaje, en cada uno de los dos meses.
-- Ingreso por viaje = total_amount. Promedio = ingreso total / viajes de esa hora
-- (no promedio de promedios, que daría mal con zonas de distinta cantidad de viajes).
with por_hora as (
    select
        d.anio_mes,
        a.hora_subida,
        sum(a.viajes) as viajes,
        sum(a.ingreso_total) / sum(a.viajes) as ingreso_promedio
    from {{ ref('agg_zone_hour') }} a
    join {{ ref('dim_date') }} d on a.fecha = d.fecha
    where d.anio_mes in ('{{ mes_asignado() }}', '{{ mes_anterior() }}')
    group by d.anio_mes, a.hora_subida
)
-- distinct on se queda con la primera fila de cada mes según el orden: la de mayor ingreso.
select distinct on (anio_mes)
    anio_mes,
    hora_subida,
    viajes,
    round(ingreso_promedio::numeric, 2) as ingreso_promedio
from por_hora
order by anio_mes desc, ingreso_promedio desc
```

## Pregunta c

**Porcentaje de viajes de marzo 2025 con `cbd_congestion_fee` mayor a 0, y las 5 zonas de origen con mayor proporción.**

**73,9 %** de los viajes aceptados de marzo 2025 pagó el cargo de congestión.

| Zona de origen | Barrio | Viajes | Con cargo | Proporción |
| --- | --- | --- | --- | --- |
| SoHo | Manhattan | 35.534 | 35.455 | 99,8 % |
| Midtown Center | Manhattan | 177.779 | 177.208 | 99,7 % |
| Union Sq | Manhattan | 112.180 | 111.825 | 99,7 % |
| East Village | Manhattan | 108.502 | 108.186 | 99,7 % |
| West Village | Manhattan | 97.373 | 97.104 | 99,7 % |

**Interpretación:** las zonas con mayor proporción están todas en el sur y centro de Manhattan, donde casi todo viaje que empieza ahí paga el cargo; el 26 % del mes que no lo pagó se reparte en zonas donde el cargo es la excepción.

Solo se consideran zonas con al menos 1.000 viajes en el mes: sin ese mínimo, el ranking lo encabezan zonas con 1 o 2 viajes al 100 %. Varias zonas empatan en 99,7 %; a igual proporción se ordena por cantidad de viajes. En marzo 2024 la columna no existía (es nula), por eso la pregunta es solo sobre el mes asignado.

Consulta: `sql/preguntas/pregunta_c_cbd_congestion.sql` (tabla `preguntas.pregunta_c_cbd_congestion`)

```sql
-- (c) Porcentaje de viajes del mes con cbd_congestion_fee > 0, y las 5 zonas de origen
-- con mayor proporción de esos viajes. Solo zonas con al menos 1.000 viajes en el mes:
-- con menos, una zona con 1 o 2 viajes aparece con 100 %.
with por_zona as (
    select
        f.pu_zone_id,
        count(*) as viajes,
        count(*) filter (where f.cbd_congestion_fee > 0) as viajes_con_cbd
    from {{ ref('fact_trips') }} f
    join {{ ref('dim_date') }} d on f.fecha = d.fecha
    where d.anio_mes = '{{ mes_asignado() }}'
    group by f.pu_zone_id
),
total_mes as (
    select round(100.0 * sum(viajes_con_cbd) / sum(viajes), 1) as pct_mes
    from por_zona
)
select
    t.pct_mes as pct_viajes_con_cbd_en_el_mes,
    z.zone as zona_origen,
    z.borough as barrio,
    p.viajes,
    p.viajes_con_cbd,
    round(100.0 * p.viajes_con_cbd / p.viajes, 1) as pct_zona
from por_zona p
join {{ ref('dim_zone') }} z on p.pu_zone_id = z.zone_id
cross join total_mes t
where p.viajes >= 1000
  and p.pu_zone_id not in (264, 265)
order by pct_zona desc, p.viajes desc
limit 5
```

## Pregunta d

**Propina promedio como porcentaje de la tarifa, por tipo de pago.**

| Tipo de pago | Forma de pago | 2025-03 viajes | 2025-03 propina | 2024-03 viajes | 2024-03 propina |
| --- | --- | --- | --- | --- | --- |
| 0 | Tarifa flexible | 916.125 | 2,00 % | 425.756 | 3,08 % |
| 1 | Tarjeta de crédito | 2.684.943 | 26,23 % | 2.596.340 | 26,23 % |
| 2 | Efectivo | 385.675 | 0,00 % | 466.287 | 0,00 % |
| 3 | Sin cargo | 17.840 | 0,09 % | 16.155 | 0,07 % |
| 4 | Disputa | 48.617 | 0,08 % | 31.386 | 0,20 % |

**Interpretación:** con tarjeta la propina promedio es del 26 % de la tarifa en los dos años; el valor del **efectivo (0 %) no es interpretable**, porque el sistema solo registra las propinas pagadas con tarjeta: la que se da en efectivo no queda en los datos, así que 0 significa "no registrada", no "no hubo propina".

Los viajes con tarifa <= 0 no entran en el promedio (su `propina_pct` es nula, regla R09). Los tipos 3 y 4 casi no tienen propina, lo que es esperable en viajes sin cargo o en disputa.

Consulta: `sql/preguntas/pregunta_d_propina_por_pago.sql` (tabla `preguntas.pregunta_d_propina_por_pago`)

```sql
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
```

## Pregunta e

**Cantidad de viajes y tarifa media de los que empiezan o terminan en JFK o LaGuardia.**

| Mes | Viajes | Tarifa media |
| --- | --- | --- |
| 2025-03 | 322.944 | 55,17 USD |
| 2024-03 | 324.235 | 55,53 USD |

**Interpretación:** los viajes de aeropuerto se mantuvieron prácticamente iguales (−0,4 % en cantidad y −0,6 % en tarifa media), y su tarifa casi triplica la media general de 19,29 USD.

Los aeropuertos se identifican por nombre de zona (`'JFK Airport'` y `'LaGuardia Airport'` en `dim_zone`), como origen o como destino.

Consulta: `sql/preguntas/pregunta_e_aeropuertos.sql` (tabla `preguntas.pregunta_e_aeropuertos`)

```sql
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
```

## Pregunta f

**Variación de viajes totales y de tarifa media entre marzo 2025 y marzo 2024.**

| | Marzo 2024 | Marzo 2025 | Variación |
| --- | --- | --- | --- |
| Viajes aceptados | 3.535.924 | 4.053.200 | +14,6 % |
| Tarifa media | 19,26 USD | 19,29 USD | +0,2 % |

**Hipótesis de causa:**

1. El aumento de viajes no es parejo: los de tipo de pago 0 (tarifa flexible) pasaron de 425.756 a 916.125.
2. Esos 490.369 viajes de más explican el 95 % del aumento; el resto de los tipos creció apenas 0,9 %.
3. Que la tarifa media no se mueva indica que no cambió el tipo de viaje, sino cuántos se registran como tarifa flexible.
4. Hipótesis: en 2025 una parte mayor de los viajes se pide y paga por aplicación y se registra con ese tipo de pago.
5. No podemos confirmarlo con estos datos; habría que comparar más meses o el origen de cada viaje.

Datos del desglose por tipo de pago: `exploracion/04_resultados.sql`.

Consulta: `sql/preguntas/pregunta_f_variacion_meses.sql` (tabla `preguntas.pregunta_f_variacion_meses`)

```sql
-- (f) Variación de viajes totales y de tarifa media entre el mes y el mismo mes de 2024.
-- Tarifa media sin los viajes con tarifa <= 0 (R09).
with por_mes as (
    select
        d.anio_mes,
        count(*) as viajes,
        avg(f.fare_amount) filter (where f.fare_amount > 0) as tarifa_media
    from {{ ref('fact_trips') }} f
    join {{ ref('dim_date') }} d on f.fecha = d.fecha
    group by d.anio_mes
)
select
    actual.viajes as viajes_mes,
    anterior.viajes as viajes_mes_anterior,
    round(100.0 * (actual.viajes - anterior.viajes) / anterior.viajes, 1) as variacion_viajes_pct,
    round(actual.tarifa_media::numeric, 2) as tarifa_media_mes,
    round(anterior.tarifa_media::numeric, 2) as tarifa_media_mes_anterior,
    round((100.0 * (actual.tarifa_media - anterior.tarifa_media) / anterior.tarifa_media)::numeric, 1) as variacion_tarifa_pct
from por_mes actual
join por_mes anterior
  on actual.anio_mes = '{{ mes_asignado() }}'
 and anterior.anio_mes = '{{ mes_anterior() }}'
```

## Verificación

Las cifras de este documento son las que devuelve `make respuestas` después de `make all MES=2025-03` (corrida del 23/11/2026). Los conteos de calidad en los que se apoyan coinciden con los de `exploracion/HALLAZGOS.md`, medidos por separado sobre los datos crudos.
