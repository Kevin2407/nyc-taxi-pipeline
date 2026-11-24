-- Reconciliación (consigna 3.4): el pipeline falla si las filas leídas no son
-- iguales a las aceptadas más las de cuarentena.
-- Un test de dbt falla cuando la consulta devuelve alguna fila: acá, cada mes que no cierra.
select
    mes_archivo,
    filas_leidas,
    filas_aceptadas,
    filas_cuarentena
from {{ ref('reporte_calidad') }}
where filas_leidas <> filas_aceptadas + filas_cuarentena
