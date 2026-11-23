"""Cálculos con meses en formato AAAA-MM."""
import re

FORMATO = re.compile(r"\d{4}-(0[1-9]|1[0-2])")


def es_mes_valido(mes):
    return bool(FORMATO.fullmatch(mes))


def mes_anterior(mes):
    """El mismo mes del año anterior: 2025-03 -> 2024-03."""
    anio, numero = mes.split("-")
    return f"{int(anio) - 1}-{numero}"


def mes_siguiente(mes):
    """El mes que sigue: 2025-03 -> 2025-04, 2025-12 -> 2026-01."""
    anio, numero = int(mes[:4]), int(mes[5:])
    if numero == 12:
        return f"{anio + 1}-01"
    return f"{anio}-{numero + 1:02d}"
