-- Filas aceptadas: no violan ninguna regla de RECHAZO. Pueden traer advertencias en flags.
select
    {{ columnas_contrato() | join(',\n    ') }},
    archivo_origen,
    mes_archivo,
    flags
from {{ ref('trips_evaluados') }}
where reglas_violadas = ''
