-- Filas rechazadas: la fila original (columnas del contrato, con sus valores sin tocar),
-- el archivo de donde vino y la lista de reglas de rechazo que viola.
select
    {{ columnas_contrato() | join(',\n    ') }},
    archivo_origen,
    mes_archivo,
    reglas_violadas
from {{ ref('trips_evaluados') }}
where reglas_violadas <> ''
