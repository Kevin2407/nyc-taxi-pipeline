from src.meses import es_mes_valido, mes_anterior, mes_siguiente


def test_calculo_de_meses():
    assert mes_anterior("2025-03") == "2024-03"
    assert mes_siguiente("2025-03") == "2025-04"
    assert mes_siguiente("2025-12") == "2026-01"
    assert es_mes_valido("2025-03")
    assert not es_mes_valido("2025-3") and not es_mes_valido("2025-13")
