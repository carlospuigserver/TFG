# rangos.py

# ———————————————————————————————————————————————
# RANGOS PRE-FLOP HEADS-UP
# ———————————————————————————————————————————————
# En HU sólo hay dos posiciones: BTN (quien abre) y BB (quien defiende).
#
# Formato: "POSICIÓN": (porcentaje_de_uso_aprox, [lista_de_manos])
# donde porcentaje_de_uso_aprox se usa a modo informativo; lo importante es la lista de manos.

PRE_FLOP_OPEN_RANGES = {
    # BTN abre aproximadamente el 50 % de las manos (ejemplo muy simplificado)
    "BTN": (
        0.50,
        [
            "AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "66",
            "AKs", "AQs", "AJs", "KQs", "AKo", "AQo", "AJo", "KQo",
            # Añade más manos si quieres expandir el rango hasta ~50 %
            "T9s", "98s", "87s", "76s", "65s",
            "KJo", "QJo", "JTo"
        ]
    )
}

# ———————————————————————————————————————————————
# RANGOS DE DEFENSA PRE-FLOP EN BB
# ———————————————————————————————————————————————
# Formato: "ESCENARIO": (porcentaje_de_uso_aprox, [lista_de_manos])
# Sólo necesitamos “BB_vs_BTN” porque en HU siempre será BTN quien abra preflop.

PRE_FLOP_CALL_RANGES = {
    "BB_vs_BTN": (
        0.35,  # aprox. 35 % de las manos
        [
            "AA", "KK", "QQ", "JJ", "TT", "99", "88",
            "AKs", "AQs", "AJs", "KQs", "AKo", "AQo", "AJo",
            "KJo", "QJo", "JTo",
            "T9s", "98s", "87s", "76s", "65s", "54s"
        ]
    )
}

# ———————————————————————————————————————————————
# FUNCIONES AUXILIARES
# ———————————————————————————————————————————————

def get_open_range(position: str):
    """
    Retorna el tuple (porcentaje, lista_de_manos) para la posición dada al abrir preflop.
    En HU, solo existe "BTN".
    Si no hay datos, devuelve (None, []).
    """
    return PRE_FLOP_OPEN_RANGES.get(position.upper(), (None, []))


def get_call_range(scenario: str):
    """
    Retorna el tuple (porcentaje, lista_de_manos) para el escenario de defensa preflop.
    En HU, solo existe "BB_vs_BTN".
    Si no hay datos, devuelve (None, []).
    """
    return PRE_FLOP_CALL_RANGES.get(scenario.upper(), (None, []))
