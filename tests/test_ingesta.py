"""Test de idempotencia de la ingesta, sin usar la red."""
import duckdb

from src import ingesta


def test_ingesta_es_idempotente(tmp_path, monkeypatch):
    monkeypatch.setattr(ingesta, "RUTA_DB", tmp_path / "test.duckdb")
    destino = tmp_path / "raw" / "yellow_tripdata_2025-03.parquet"

    descargas = []

    def descarga_falsa(url, ruta):
        """Reemplaza la descarga real: escribe un Parquet de 3 filas y la anota."""
        descargas.append(url)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        duckdb.sql(f"COPY (SELECT * FROM range(3)) TO '{ruta}' (FORMAT parquet)")

    monkeypatch.setattr(ingesta, "descargar", descarga_falsa)

    def filas_del_log():
        con = duckdb.connect(str(ingesta.RUTA_DB))
        filas = con.execute("SELECT filas, estado FROM ingestion_log").fetchall()
        con.close()
        return filas

    # Primera corrida: descarga y registra.
    assert ingesta.ingestar("http://falso/archivo", destino)
    assert len(descargas) == 1
    assert filas_del_log() == [(3, "ok")]

    # Segunda corrida: el archivo existe y su hash coincide; no descarga ni registra.
    assert ingesta.ingestar("http://falso/archivo", destino)
    assert len(descargas) == 1
    assert filas_del_log() == [(3, "ok")]

    # Si el archivo se corrompe, el hash ya no coincide y vuelve a descargar.
    with open(destino, "ab") as archivo:
        archivo.write(b"basura")
    assert ingesta.ingestar("http://falso/archivo", destino)
    assert len(descargas) == 2