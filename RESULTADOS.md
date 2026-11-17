# Resultados

Mes asignado: **marzo 2025**, comparado contra **marzo 2024**. Se obtienen con:

```bash
python -m src.modelo --mes 2025-03
```

Todas las consultas corren sobre el modelo estrella (`fact_trips`, `dim_zone`, `dim_date`, `agg_zone_hour`), que contiene solo los viajes aceptados por las reglas de calidad: 3.535.924 de marzo 2024 y 4.053.200 de marzo 2025. Criterios comunes:

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

Consulta: `sql/preguntas/a_top10_zonas_origen.sql`

```sql
-- (a) Las 10 zonas de origen con más viajes en el mes y su variación contra el mismo mes del año anterior.
-- Se excluyen las zonas 264 (Unknown) y 265 (Outside of NYC): no son un lugar (regla R11).
WITH viajes_por_zona AS (
    SELECT
        a.pu_zone_id,
        sum(a.viajes) FILTER (WHERE d.anio_mes = '{mes}') AS viajes_mes,
        sum(a.viajes) FILTER (WHERE d.anio_mes = '{mes_anterior}') AS viajes_mes_anterior
    FROM agg_zone_hour a
    JOIN dim_date d ON a.fecha = d.fecha
    WHERE a.pu_zone_id NOT IN (264, 265)
    GROUP BY a.pu_zone_id
)
SELECT
    z.zone AS zona_origen,
    z.borough AS barrio,
    v.viajes_mes,
    v.viajes_mes_anterior,
    round(100.0 * (v.viajes_mes - v.viajes_mes_anterior) / v.viajes_mes_anterior, 1) AS variacion_pct
FROM viajes_por_zona v
JOIN dim_zone z ON v.pu_zone_id = z.zone_id
ORDER BY v.viajes_mes DESC
LIMIT 10;
```

## Pregunta b

**La hora del día con mayor ingreso promedio por viaje.**

| Mes | Hora | Viajes en esa hora | Ingreso promedio por viaje |
| --- | --- | --- | --- |
| 2025-03 | 5 (5:00 a 5:59) | 32.592 | 33,75 USD |
| 2024-03 | 5 (5:00 a 5:59) | 22.684 | 35,19 USD |

**Interpretación:** a las 5 de la mañana hay pocos viajes pero largos: el 18 a 21 % toca un aeropuerto (contra 8 a 9 % en el resto del día) y la distancia media es de 5,7 millas contra 3,3 (datos de `exploracion/explorar_resultados.py`).

El ingreso es `total_amount`. El promedio se calcula como ingreso total / viajes de la hora, a partir de `agg_zone_hour`.

Consulta: `sql/preguntas/b_hora_mayor_ingreso.sql`

```sql
-- (b) La hora del día con mayor ingreso promedio por viaje, en cada uno de los dos meses.
-- Ingreso por viaje = total_amount. Promedio = ingreso total / viajes de esa hora.
SELECT
    d.anio_mes,
    a.hora_subida,
    sum(a.viajes) AS viajes,
    round(sum(a.ingreso_total) / sum(a.viajes), 2) AS ingreso_promedio
FROM agg_zone_hour a
JOIN dim_date d ON a.fecha = d.fecha
WHERE d.anio_mes IN ('{mes}', '{mes_anterior}')
GROUP BY d.anio_mes, a.hora_subida
QUALIFY row_number() OVER (
    PARTITION BY d.anio_mes
    ORDER BY sum(a.ingreso_total) / sum(a.viajes) DESC
) = 1
ORDER BY d.anio_mes DESC;
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

Consulta: `sql/preguntas/c_cbd_congestion.sql`

```sql
-- (c) Porcentaje de viajes del mes con cbd_congestion_fee > 0, y las 5 zonas de origen
-- con mayor proporción de esos viajes. Solo zonas con al menos 1.000 viajes en el mes:
-- con menos, una zona con 1 o 2 viajes aparece con 100 %.
WITH por_zona AS (
    SELECT
        f.pu_zone_id,
        count(*) AS viajes,
        count(*) FILTER (WHERE f.cbd_congestion_fee > 0) AS viajes_con_cbd
    FROM fact_trips f
    JOIN dim_date d ON f.fecha = d.fecha
    WHERE d.anio_mes = '{mes}'
    GROUP BY f.pu_zone_id
),
total_mes AS (
    SELECT round(100.0 * sum(viajes_con_cbd) / sum(viajes), 1) AS pct_mes
    FROM por_zona
)
SELECT
    t.pct_mes AS pct_viajes_con_cbd_en_el_mes,
    z.zone AS zona_origen,
    z.borough AS barrio,
    p.viajes,
    p.viajes_con_cbd,
    round(100.0 * p.viajes_con_cbd / p.viajes, 1) AS pct_zona
FROM por_zona p
JOIN dim_zone z ON p.pu_zone_id = z.zone_id
CROSS JOIN total_mes t
WHERE p.viajes >= 1000
  AND p.pu_zone_id NOT IN (264, 265)
ORDER BY pct_zona DESC, p.viajes DESC
LIMIT 5;
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

Consulta: `sql/preguntas/d_propina_por_pago.sql`

```sql
-- (d) Propina promedio como porcentaje de la tarifa, por tipo de pago, en los dos meses.
-- propina_pct es nula cuando la tarifa es <= 0 (regla R09); avg() ignora esos viajes.
SELECT
    d.anio_mes,
    f.payment_type,
    CASE f.payment_type
        WHEN 0 THEN 'Tarifa flexible'
        WHEN 1 THEN 'Tarjeta de crédito'
        WHEN 2 THEN 'Efectivo'
        WHEN 3 THEN 'Sin cargo'
        WHEN 4 THEN 'Disputa'
        WHEN 5 THEN 'Desconocido'
        WHEN 6 THEN 'Viaje anulado'
    END AS forma_pago,
    count(*) AS viajes,
    round(avg(f.propina_pct), 2) AS propina_promedio_pct
FROM fact_trips f
JOIN dim_date d ON f.fecha = d.fecha
WHERE d.anio_mes IN ('{mes}', '{mes_anterior}')
GROUP BY d.anio_mes, f.payment_type
ORDER BY d.anio_mes DESC, f.payment_type;
```

## Pregunta e

**Cantidad de viajes y tarifa media de los que empiezan o terminan en JFK o LaGuardia.**

| Mes | Viajes | Tarifa media |
| --- | --- | --- |
| 2025-03 | 322.944 | 55,17 USD |
| 2024-03 | 324.235 | 55,53 USD |

**Interpretación:** los viajes de aeropuerto se mantuvieron prácticamente iguales (−0,4 % en cantidad y −0,6 % en tarifa media), y su tarifa casi triplica la media general de 19,29 USD.

Los aeropuertos se identifican por nombre de zona (`'JFK Airport'` y `'LaGuardia Airport'` en `dim_zone`), como origen o como destino.

Consulta: `sql/preguntas/e_aeropuertos.sql`

```sql
-- (e) Viajes y tarifa media de los que empiezan o terminan en JFK o LaGuardia,
-- identificados por nombre de zona. Tarifa media sin los viajes con tarifa <= 0 (R09).
SELECT
    d.anio_mes,
    count(*) AS viajes,
    round(avg(f.fare_amount) FILTER (WHERE f.fare_amount > 0), 2) AS tarifa_media
FROM fact_trips f
JOIN dim_date d ON f.fecha = d.fecha
JOIN dim_zone zo ON f.pu_zone_id = zo.zone_id
JOIN dim_zone zd ON f.do_zone_id = zd.zone_id
WHERE d.anio_mes IN ('{mes}', '{mes_anterior}')
  AND (zo.zone IN ('JFK Airport', 'LaGuardia Airport')
       OR zd.zone IN ('JFK Airport', 'LaGuardia Airport'))
GROUP BY d.anio_mes
ORDER BY d.anio_mes DESC;
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

Datos del desglose por tipo de pago: `exploracion/explorar_resultados.py`.

Consulta: `sql/preguntas/f_variacion_meses.sql`

```sql
-- (f) Variación de viajes totales y de tarifa media entre el mes y el mismo mes del año anterior.
-- Tarifa media sin los viajes con tarifa <= 0 (R09).
WITH por_mes AS (
    SELECT
        d.anio_mes,
        count(*) AS viajes,
        avg(f.fare_amount) FILTER (WHERE f.fare_amount > 0) AS tarifa_media
    FROM fact_trips f
    JOIN dim_date d ON f.fecha = d.fecha
    GROUP BY d.anio_mes
)
SELECT
    actual.viajes AS viajes_mes,
    anterior.viajes AS viajes_mes_anterior,
    round(100.0 * (actual.viajes - anterior.viajes) / anterior.viajes, 1) AS variacion_viajes_pct,
    round(actual.tarifa_media, 2) AS tarifa_media_mes,
    round(anterior.tarifa_media, 2) AS tarifa_media_mes_anterior,
    round(100.0 * (actual.tarifa_media - anterior.tarifa_media) / anterior.tarifa_media, 1) AS variacion_tarifa_pct
FROM por_mes actual
JOIN por_mes anterior ON actual.anio_mes = '{mes}' AND anterior.anio_mes = '{mes_anterior}';
```
