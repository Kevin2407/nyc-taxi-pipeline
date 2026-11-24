"""Parte 2: el contrato de esquema. Tests sin base de datos (solo el esquema del archivo)."""
import pyarrow as pa

from src.esquema import ajustar_al_contrato, cargar_contrato, comparar, cumple
from tests.conftest import parquet_sintetico


def test_columna_opcional_faltante_se_carga_nula():
    """Un archivo como los de 2024 (sin cbd_congestion_fee) cumple, y la columna queda nula."""
    contrato = cargar_contrato()
    tabla = parquet_sintetico()
    reporte = comparar(tabla.schema, contrato)
    assert reporte["faltantes_opcionales"] == ["cbd_congestion_fee"]
    assert cumple(reporte)
    ajustada = ajustar_al_contrato(tabla, contrato)
    assert ajustada.column_names == [c["name"] for c in contrato["columns"]]  # snake_case y en orden
    assert ajustada["cbd_congestion_fee"].null_count == tabla.num_rows


def test_columna_nueva_se_reporta_y_no_se_carga():
    contrato = cargar_contrato()
    tabla = parquet_sintetico().append_column("ColumnaNueva", pa.array(["x", "y", "z"]))
    reporte = comparar(tabla.schema, contrato)
    assert reporte["nuevas"] == ["columna_nueva"]
    assert cumple(reporte)  # una columna nueva no frena el pipeline
    assert "columna_nueva" not in ajustar_al_contrato(tabla, contrato).column_names


def test_tipo_distinto_o_columna_obligatoria_faltante_frenan():
    contrato = cargar_contrato()
    tabla = parquet_sintetico()
    con_otro_tipo = tabla.set_column(0, "VendorID", pa.array(["2", "2", "2"]))
    assert not cumple(comparar(con_otro_tipo.schema, contrato))
    sin_obligatoria = tabla.drop_columns(["trip_distance"])
    reporte = comparar(sin_obligatoria.schema, contrato)
    assert reporte["faltantes_obligatorias"] == ["trip_distance"]
    assert not cumple(reporte)
