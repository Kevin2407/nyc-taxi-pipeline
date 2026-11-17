"""Datos de apoyo para interpretar las preguntas (b) y (f) de RESULTADOS.md.

Se ejecuta desde la raíz del repo, después del pipeline:  python exploracion/explorar_resultados.py
"""
import duckdb

con = duckdb.connect("data/taxi.duckdb", read_only=True)

print("(b) La hora 5 contra el resto: peso de los aeropuertos y distancia media")
con.sql("""
    SELECT
        d.anio_mes,
        f.hora_subida = 5 AS es_hora_5,
        round(100.0 * count(*) FILTER (WHERE f.pu_zone_id IN (132, 138) OR f.do_zone_id IN (132, 138))
              / count(*), 1) AS pct_viajes_aeropuerto,
        round(avg(f.trip_distance) FILTER (WHERE f.trip_distance > 0), 2) AS distancia_media
    FROM fact_trips f
    JOIN dim_date d ON f.fecha = d.fecha
    GROUP BY ALL
    ORDER BY d.anio_mes, es_hora_5
""").show()

print("(f) Viajes aceptados por tipo de pago 0 contra el resto")
con.sql("""
    SELECT
        d.anio_mes,
        f.payment_type = 0 AS es_tarifa_flexible,
        count(*) AS viajes
    FROM fact_trips f
    JOIN dim_date d ON f.fecha = d.fecha
    GROUP BY ALL
    ORDER BY d.anio_mes, es_tarifa_flexible
""").show()
con.close()
