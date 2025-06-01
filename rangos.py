# rangos.py

import random

# ———————————————————————————————————————————————
# RANGOS PRE-FLOP: “Raise First In” + % de uso por posición
# ———————————————————————————————————————————————
# Formato: POSICIÓN: (PORCENTAJE_APROX, [lista_de_manos])
PRE_FLOP_OPEN_RANGES = {
    "UTG": (
        0.09,  # ≈9% del mazo
        [
            "66", "77", "88", "99", "TT", "JJ", "QQ", "KK", "AA",
            "AJs", "KQs",
            "AJo", "KQo"
        ]
    ),
    "EP": (
        0.15,  # ≈15% del mazo
        [
            "22", "33", "44", "55", "66", "77", "88", "99", "TT", "JJ", "QQ", "KK", "AA",
            "ATs", "KJs", "QJs", "JTs", "T9s", "98s", "87s", "76s", "65s",
            "AJo", "KJo", "QJo"
        ]
    ),
    "MP": (
        0.20,  # ≈20% del mazo
        [
            "22", "33", "44", "55", "66", "77", "88", "99", "TT", "JJ", "QQ", "KK", "AA",
            "ATs", "KTs", "QTs", "J9s", "T8s", "98s", "87s", "76s", "65s", "54s",
            "ATo", "KTo", "QTo", "JTo"
        ]
    ),
    "HJ": (
        0.25,  # ≈25% del mazo
        [
            "22", "33", "44", "55", "66", "77", "88", "99", "TT", "JJ", "QQ", "KK", "AA",
            "A7s", "K9s", "Q9s", "J9s", "T8s", "97s", "86s", "75s", "64s", "54s",
            "A9o", "KTo", "QTo", "JTo", "T9o"
        ]
    ),
    "CO": (
        0.35,  # ≈35% del mazo
        [
            "22", "33", "44", "55", "66", "77", "88", "99", "TT", "JJ", "QQ", "KK", "AA",
            "A2s", "K8s", "Q8s", "J8s", "T7s", "97s", "86s", "75s", "64s", "54s", "43s",
            "A8o", "A5o", "A4o", "A3o", "A2o", "K9o", "Q9o", "J9o", "T9o"
        ]
    ),
    "BTN": (
        0.50,  # ≈50% del mazo
        [
            "22", "33", "44", "55", "66", "77", "88", "99", "TT", "JJ", "QQ", "KK", "AA",
            "A2s", "K2s", "Q7s", "J7s", "T7s", "96s", "86s", "75s", "64s", "53s", "43s",
            "A2o", "A3o", "A4o", "A5o", "K5o", "Q8o", "J8o", "T8o", "98o", "87o", "76o", "65o"
        ]
    )
}

# Ejemplo de uso:
# porcentaje_utg, utg_hands = PRE_FLOP_OPEN_RANGES["UTG"]
# print(f"UTG abre ~{porcentaje_utg*100:.0f}% con estas manos: {utg_hands}")


# ———————————————————————————————————————————————
# RANGOS PRE-FLOP: “Call vs Open-Raise” + % de uso en cada escenario
# ———————————————————————————————————————————————
# Formato: ESCENARIO: (PORCENTAJE_APROX, [lista_de_manos])
PRE_FLOP_CALL_RANGES = {
    "BTN_vs_EP": (
        0.08,  # ≈8% vs open-raise de EP
        [
            "22", "33", "44", "55", "66", "77", "88", "99", "TT", "JJ",
            "AQs", "AJs", "KQs",
            "AQo", "AJo", "KQo"
        ]
    ),
    "BB_vs_EP": (
        0.13,  # ≈13% vs open-raise de EP
        [
            "22", "33", "44", "55", "66", "77", "88", "99", "TT", "JJ",
            "AQs", "ATs", "KJs", "QJs", "JTs",
            "T9s", "98s", "87s", "76s", "65s", "54s",
            "AQo", "ATo", "KJo", "QJo"
        ]
    ),
    "BTN_vs_MP": (
        0.16,  # ≈16% vs open-raise de MP
        [
            "22", "33", "44", "55", "66", "77", "88", "99", "TT",
            "AJs", "ATs",
            "KTs", "QTs", "J9s", "T8s", "98s", "87s", "76s", "65s", "54s",
            "AJo", "ATo", "KTo", "QTo", "JTo"
        ]
    ),
    "BB_vs_MP": (
        0.22,  # ≈22% vs open-raise de MP
        [
            "22", "33", "44", "55", "66", "77", "88", "99", "TT",
            "AJs", "ATs", "K9s", "Q9s", "J9s", "T8s", "97s", "86s", "75s", "64s", "53s", "43s",
            "AJo", "A9o", "KTo", "QTo", "JTo"
        ]
    ),
    "BB_vs_LP": (
        0.30,  # ≈30% vs open-raise de LP (CO/BOTÓN)
        [
            "22", "33", "44", "55", "66", "77", "88", "99", "TT",
            "ATs", "A9s", "A8s", "A7s", "A6s", "A5s", "A4s", "A3s", "A2s",
            "KJs", "KTs", "K9s", "K8s", "Q8s", "J8s", "T7s", "96s", "85s", "74s", "63s", "53s", "43s",
            "ATo", "A7o", "KJo", "K9o", "Q9o", "J9o", "T9o", "98o", "87o", "76o", "65o"
        ]
    )
}

# Ejemplo de uso:
# pct_bb_vs_ep, bb_vs_ep_hands = PRE_FLOP_CALL_RANGES["BB_vs_EP"]
# print(f"BB defiende ~{pct_bb_vs_ep*100:.0f}% con estas manos: {bb_vs_ep_hands}")


# ———————————————————————————————————————————————
# REGLAS DE TAMAÑO DE APUESTA (Bet Sizing Rules)
# ———————————————————————————————————————————————
# Fuente: UpswingPoker – “Bet Sizing Strategy: 8 Rules to Help You Choose the Perfect Bet Size”
#
# Estas reglas definen recomendaciones generales de tamaño de apuesta
# en distintas situaciones de no-limit Texas Hold’em.

BET_SIZING_RULES = {
    1: {
        "title": "Aumenta tu apuesta preflop cuando haya un jugador débil en las ciegas",
        "description": (
            "Si el jugador en la ciega tiende a pagar con muchos rangos (‘static calling range’), "
            "aumenta tu open-raise (por ejemplo, de 2.5bb a 3.5bb) para extraer más valor. "
            "Los jugadores débiles no ajustan su rango de defensa según el tamaño del raise, "
            "así que usar un raise mayor incrementa tu EV."
        ),
        "example": (
            "Si crees que el villano en BB pagará tu raise con las mismas manos tanto si apuestas 2.5bb como 3.5bb, "
            "conviene 3.5bb para ganar más en promedio."
        )
    },
    2: {
        "title": "3-bet más grande preflop si quedarás fuera de posición postflop",
        "description": (
            "Cuando planeas ver postflop fuera de posición, realiza un 3-bet de aproximadamente "
            "4× el tamaño original de la apuesta. En cambio, si estás en posición, bastará con ~3×. "
            "El objetivo es hacer que tu oponente pague un precio alto para verte fuera de posición, "
            "donde su equity es más fácil de realizar."
        ),
        "example": (
            "Si el héroe está en BTN versus un raise de 3bb de MP y va a estar en posición, su 3-bet sería ~9bb. "
            "Pero si está en SB versus ese MP y quedará fuera de posición, 3-betearía ~12bb."
        )
    },
    3: {
        "title": "Apuesta pequeña (25-35% del bote) en flops secos y estáticos",
        "description": (
            "En tableros donde la mayoría de las manos de tu oponente tienen poca equity (por ejemplo, "
            "A♣ 8♠ 3♣ sin proyecto), tu apuesta principal es extraer valor con tus manos fuertes y negar equity. "
            "Sin embargo, en estos flops, la capacidad de negar equity es menor (poca probabilidad de que te remonten), "
            "por lo que puedes apostar pequeño (~25-35% del bote). Además, el rango de call del villano "
            "suele ser inelástico, es decir, pagará o foldeará casi igual con tamaños entre 25-100%."
        ),
        "example": (
            "Flop 5.5bb: A♦ 8♠ 3♣ (board seco). Una apuesta de 1.8bb (~33%) es óptima "
            "para extraer valor y mantener presión sin arriesgar demasiado."
        )
    },
    4: {
        "title": "Apuesta grande (55-80% del bote) en flops “húmedos” y dinámicos",
        "description": (
            "Cuando el tablero presenta muchos proyectos (por ejemplo, A♠ 9♥ 5♠ 4♠), tu rango de valor "
            "puede ser vulnerado con proyectos de color o escalera. Apostar grande (~55-80%) construye el bote "
            "con tus manos hechas y dificulta que te paguen con proyectos baratos. También genera mayor fold equity "
            "para tus bluffs en flops dinámicos."
        ),
        "example": (
            "Flop 34.5bb: 2♠ 5♥ 3♠ (board húmedo). Una apuesta de 12bb (~35%) sería demasiado pequeña; "
            "conviene ~60% (20-22bb) porque muchos turn cards mejoran proyectos y quieres proteger tu equity."
        )
    },
    5: {
        "title": "El stack-to-pot ratio (SPR) debe influir en tu tamaño de apuesta",
        "description": (
            "Antes de elegir tamaño, piensa en el tamaño del pote en calles futuras y cómo quieres jugar "
            "tus valor hands y bluffs. Si apuestas muy grande temprano y te comprometes mucho del stack, "
            "puede que no te queden fichas para bluffear en el river. Ajusta tu apuesta para permitir "
            "un rango de maniobras correcto en turn/river."
        ),
        "example": (
            "Si en el flop 5,250 con SPR alto, apostar 3,000 en lugar de 5,000 te permitirá tener fichas para "
            "bluffear o extraer más valor en turn/river. Un 65% flotante en flop deja SPR razonable."
        )
    },
    6: {
        "title": "Overbet cuando tienes ventaja nut",
        "description": (
            "Si tu rango percibido supera al de tu oponente en fuerza de mano (por ejemplo, solo tú puedes "
            "tener el nut flush en cierta textura), considera una overbet (>100% del bote). Esto maximiza el valor "
            "con manos nuts y genera gran fold equity con bluffs polarizados."
        ),
        "example": (
            "River: 3♠ 5♠ A♥ Q♦ 7♦. Tienes A♦ K♠ (nut flush). Villano hace pot-size bet. "
            "Al overbetear 2× bote, explotas la baja probabilidad de que te igualen con una mano mejor, "
            "y tus bluffs (por ejemplo, bloqueadores de nuts) cobran más fold equity."
        )
    },
    7: {
        "title": "Apuesta al menos 66% del bote en el turn cuando hagas la segunda barrel",
        "description": (
            "Al “double-barrelear” (apostar flop y turn), usa un tamaño grande (~66% o más) en turn. "
            "Tu rango debe estar polarizado: buenas manos para value bets y bluffs con equity de mejora. "
            "Un tamaño inferior reduce tu fold equity y disminuye el EV total."
        ),
        "example": (
            "Si en el flop apostaste 33% y te pagaron, en el turn apuesta al menos 66% para mantener polarización "
            "y evitar que tu oponente controle el pote con manos medias."
        )
    },
    8: {
        "title": "Usa c-bet pequeño (25-40% del bote) en 3-bet pots",
        "description": (
            "En botes que ya fueron 3-beteados preflop, el SPR suele ser bajo. "
            "Una c-bet de ~25-40% del bote sigue permitiendo que puedas comprometerte en calles posteriores "
            "y presiona eficientemente al enemigo. Muchos solvers prefieren estos tamaños en 3-bet pots, "
            "tanto in como out of position."
        ),
        "example": (
            "Si preflop se jugó 3-bet pot de 15bb y llegas al flop con 80bb atrás, una c-bet de 25-30% "
            "te deja fichas para una segunda o tercera barrel en turn/river."
        )
    }
}

# Ejemplo de uso:
# for rule_num, info in BET_SIZING_RULES.items():
#     print(f"Regla {rule_num}: {info['title']}")
#     print(f"  Descripción: {info['description']}")
#     print(f"  Ejemplo: {info['example']}\n")


# ———————————————————————————————————————————————
# TIPS DE RIVER: “4 Tips That Will Help You Win More Money On the River”
# ———————————————————————————————————————————————
# Fuente: UpswingPoker – “4 Tips That Will Help You Win More Money On the River”
#
# Estas recomendaciones ayudan en la toma de decisiones en el river:
# 1. Practica definir rangos fuera de la mesa.
# 2. Usa pot odds al llamar y apostar.
# 3. Enfócate en card removal (bloqueadores) cuando bluffees en el river.
# 4. Considera un overbet cuando tu rango esté polarizado.

RIVER_TIPS = {
    1: {
        "title": "Practica definir rangos fuera de la mesa",
        "description": (
            "A medida que avanza la mano, el rango del oponente se va definiendo cada vez más. "
            "En el river, su rango es el más estrecho. Antes de que actúe, repasa mentalmente:\n"
            "  • Posición del oponente.\n"
            "  • Rango preflop estimado según su posición y acción.\n"
            "  • Acciones postflop: c-bets, check-backs, raises, tamaños.\n"
            "  • Cómo la textura del board afectó su rango.\n"
            "En cada calle, pregúntate:\n"
            "  - ¿Cuál era su rango preflop?\n"
            "  - ¿Qué manos habrían c-beteado vs. hecho check-back?\n"
            "  - ¿Su rango quedó capado al no apostar en el turn?\n"
            "Evita pensar ‘absoluto’: un buen oponente mezclará frecuencias. Aunque parezca imposible que tenga AA, "
            "no lo descartarás por completo si alguna línea lo sugiere."
        ),
        "example": (
            "Ejercicio fuera de la mesa: Dibuja un flop y enumerar las manos que c-betearían vs. las que check-backearían. "
            "Al llegar al turn y al river, elimina combos según la acción. Este hábito te facilitará el river."
        )
    },
    2: {
        "title": "Usa pot odds al llamar y apostar",
        "description": (
            "En el river no hay más calles, por lo que las pot odds son la métrica clave:\n"
            "  • Para calcular la frecuencia de winrate necesaria al llamar:\n"
            "    (Bet del villano / (Tamaño total del pote si pagas)) × 100\n"
            "    Necesitas esa proporción como equity mínima.\n"
            "  • Para calcular la frecuencia de fold necesaria al bluffear:\n"
            "    (Tu bet / (Tamaño del pote incluyendo tu bet)) × 100\n"
            "    Necesitas esa proporción de folds para que tu bluff sea rentable.\n"
            "Algunos ejemplos:\n"
            "  - Villano apuesta $30 en pote $50:\n"
            "    Necesitas ganar más de (30 / (50+30+30))×100 ≈ 27.3% para que el call sea +EV.\n"
            "  - Bluff de $30 en pote $50:\n"
            "    Necesitas que el villano foldee más de (30 / (50+30))×100 = 37.5%.\n"
        ),
        "example": (
            "Ejercicio: Villano apuesta $150 en pote $300 → (150 / (300+150+150)) ×100 = 25%.\n"
            "   Necesitas tener la mejor mano >25% para llamar.\n"
            "Otro: Tú bluffeas $85 en pote $150 → (85 / (150+85)) ×100 ≈ 36.2%.\n"
            "   Necesitas que foldeen >36.2% para que tu bluff sea rentable."
        )
    },
    3: {
        "title": "Enfócate en card removal (bloqueadores) cuando bluffees en el river",
        "description": (
            "En el river, las bluffs tienen 0% de equity si te pagan, así que escogerás bluffs basados en bloqueadores:\n"
            "  • Tu mano debería eliminar combinaciones clave del rango de valor del oponente.\n"
            "  • En el river, el rango del rival es muy estrecho, así que bloquear 1–2 combos reduce significativamente "
            "sus posibles manos ganadoras.\n"
            "Al llamar en spots marginales, considera cuáles de tus cartas bloquean las posibles manos de valor "
            "del oponente para decidir si vale la pena pagar."
        ),
        "example": (
            "Board: 9♦ 6♦ 5♦ J♣ 3♥. Tú tienes A♦ 2♦:\n"
            "  • Bloqueas todas las combinaciones de A♦X♦ que completan el nut flush.\n"
            "  • Si villano apostó, es improbable que tenga el nut flush.\n"
            "  • Overbluff con A♦2♦: máximo fold equity y gran bloqueador de nuts."
        )
    },
    4: {
        "title": "Considera un overbet cuando tu rango esté polarizado",
        "description": (
            "En spots polarizados de river (tu rango = manos muy fuertes vs. bluffs puros), un overbet puede:\n"
            "  • Maximizar valor con tus manos nuts.\n"
            "  • Generar fold equity masiva con tus bluffs.\n"
            "El momento adecuado es cuando tu oponente casi jamás puede tener mejores manos en su rango. "
            "Verifica que sus líneas anteriores indican falta de nuts posibles."
        ),
        "example": (
            "Ejemplo Doug vs. Sauce123:\n"
            "  • Board: 9♦ 6♦ 5♦ J♣ 3♥. Doug con A♦2♦ (bloqueador nuts).\n"
            "  • Villano chequea flop y turn → improbable que tenga flush.\n"
            "  • Doug overbetea ~2× bote en el river → máxima fold equity con A♦2♦ como bluff, "
            "y valor con combos de nuts (A♦4♦, A♦6♦, etc.)."
        )
    }
}

# ———————————————————————————————————————————————
# PRINCIPIOS DE HAND-READING (Tácticas vs. Estrategias)
# ———————————————————————————————————————————————
# Fuente: Red Chip Poker – “Poker Strategy And Tactics Are Not The Same” (Kat Martin)
#
# Distinguir estrategia (rangos preflop, fundamentales GTO) de tácticas (jugadas con EV definido,
# explotar errores del oponente, spots all-in y river bluffs calculables). A continuación, 7 principios
# para desarrollar la habilidad de leer manos postflop:

HAND_READING_PRINCIPLES = [
    {
        "id": 1,
        "title": "Enfócate en lo que es probable (Not what’s merely possible)",
        "description": (
            "Descarta manos que son remotamente posibles pero no plausibles según las acciones anteriores. "
            "Cada acción (apuesta, check, raise) filtra el rango. Al ver showdown, corrige tu modelo para futuros spots."
        )
    },
    {
        "id": 2,
        "title": "Rangos capados (Capped Ranges)",
        "description": (
            "Identifica cuándo las acciones de tu oponente limitan su rango (por ejemplo, check en flop indica "
            "que no tiene ciertas manos fuertes). Si ven pasivo en calles tempranas, su rango es más amplio pero "
            "menos fuerte. Si ven agresión, su rango es más estrecho y fuerte."
        )
    },
    {
        "id": 3,
        "title": "Líneas inusuales suelen indicar valor fuerte",
        "description": (
            "Acciones inesperadas (check-raise, overbets, buses atípicos) con alta frecuencia son más probables "
            "de ser valor que bluffs, porque la mayoría de jugadores no crean líneas tan complejas con bluffs."
        )
    },
    {
        "id": 4,
        "title": "Descenso por el árbol de apuestas (Down the Betting Tree)",
        "description": (
            "Cuanto más profunda en la mano, más se desvían los jugadores de líneas GTO. Flop y turn típicamente "
            "siguen rangos cercanos a GTO, pero 3-bets de flop y raises de turn/river son raros en la práctica, "
            "y usualmente indican valor."
        )
    },
    {
        "id": 5,
        "title": "Telltales de tamaños de apuesta (Sizing Tells)",
        "description": (
            "En hold’em, pot-size bets suelen indicar manos muy fuertes. Overbets también son fuertes, "
            "pero pueden esconder un rango algo más débil que una apuesta al pote. Overbet jams (all-in) "
            "también suelen ser más débiles que un simple overbet."
        )
    },
    {
        "id": 6,
        "title": "Perfiles de jugadores (Player Profiles)",
        "description": (
            "Si conoces al oponente, aprovecha su tendencia. Recreacionales bluffean más que regs → bluff-catch "
            "más contra recs. En el river, recs “mergean” (apostarán manos medias como valor), mientras que regs "
            "tienden a polarizar."
        )
    },
    {
        "id": 7,
        "title": "Textura del board (Board Texture)",
        "description": (
            "La textura, combinada con las acciones, define qué manos puede tener tu rival. Si el flop era seco y "
            "ven check-check, su rango es muy desfavorable. En boards draw-heavy, presta atención a proyectos "
            "que puedan comprar en turn/river."
        )
    }
]


# ———————————————————————————————————————————————
# FUNCIONES AUXILIARES DE HAND-READING
# ———————————————————————————————————————————————

def compute_pot_odds_to_call(villain_bet, current_pot):
    """
    Calcula el porcentaje mínimo de veces que necesitas tener la mejor mano para que un call en el river sea rentable.
    Fórmula: (villain_bet / (current_pot + villain_bet + villain_bet)) * 100
    """
    total_if_called = current_pot + villain_bet + villain_bet
    return (villain_bet / total_if_called) * 100 if total_if_called > 0 else 0.0


def compute_pot_odds_to_bluff(bluff_bet, current_pot):
    """
    Calcula el porcentaje mínimo de veces que el villano debe foldear para que tu bluff en el river sea rentable.
    Fórmula: (bluff_bet / (current_pot + bluff_bet)) * 100
    """
    total_with_bluff = current_pot + bluff_bet
    return (bluff_bet / total_with_bluff) * 100 if total_with_bluff > 0 else 0.0


# Ejemplos de uso:
# call_freq = compute_pot_odds_to_call(villain_bet=30, current_pot=50)
# bluff_freq = compute_pot_odds_to_bluff(bluff_bet=30, current_pot=50)
# print(f"Necesitas ganar >{call_freq:.1f}% para call en river.")
# print(f"Necesitas que villano foldee >{bluff_freq:.1f}% para bluffear.")


# ———————————————————————————————————————————————
# ESTRATEGIA vs. TÁCTICAS
# ———————————————————————————————————————————————
# Fuente: Kat Martin – “Poker Strategy And Tactics Are Not The Same”
#
# - Estrategia: decidida temprano (rangos preflop, fundamento GTO). Normalmente no conocemos EV exacto.
# - Tácticas: spots con EV definido (all-in preflop, river bluffs, river calls). Se basan en cálculos simplificados
#   (“vacuumed EV analysis”) o datos poblacionales (“Deviate”).
#
# A continuación, se resumen algunos conceptos clave:

PT_DISTINCTION = {
    "strategy": {
        "definition": (
            "Decisiones de rango y lineamientos basados en teoría (GTO, rangos preflop). "
            "No se conoce EV exacto en cada mano; se confía en fundamentos teóricos empíricos."
        ),
        "example": (
            "Rango de open-raise UTG basado en soluciones GTO o en rangos predefinidos de apps GTO."
        )
    },
    "tactics": {
        "definition": (
            "Jugadas específicas con EV calculable (all-in preflop, river bets en spots calculables). "
            "Se basan en datos de población (spot donde muchos jugadores overfold) o análisis simples de EV."
        ),
        "example": (
            "Bluff al river con A♦2♦ en board 9♦6♦5♦J♣3♥ porque casi nadie tiene flush; EV calculable mediante pot odds."
        )
    }
}


# ———————————————————————————————————————————————
# FUNCIONES AUXILIARES (Ejemplos de cómo usar estos rangos en tu bot)
# ———————————————————————————————————————————————

def get_open_range(position):
    """
    Retorna el tuple (porcentaje, lista_de_manos) para la posición dada al abrir preflop.
    Si no existe la posición, retorna (None, []).
    """
    return PRE_FLOP_OPEN_RANGES.get(position.upper(), (None, []))


def get_call_range(scenario):
    """
    Retorna el tuple (porcentaje, lista_de_manos) para el escenario de defensa preflop.
    Si no existe el escenario, retorna (None, []).
    """
    return PRE_FLOP_CALL_RANGES.get(scenario.upper(), (None, []))


def suggest_bet_size(board_texture, street, in_3bet_pot=False):
    """
    Devuelve un rango sugerido de porcentaje del pote a apostar según la textura del board y la calle.
    - board_texture: 'dry', 'wet', 'neutral'
    - street: 'flop', 'turn', 'river'
    - in_3bet_pot: True si el bote fue 3-beteado preflop
    """
    if street == "flop":
        if in_3bet_pot:
            # Regla #8
            return (0.25, 0.40)  # c-bet del 25-40% del bote
        else:
            if board_texture == "dry":
                # Regla #3
                return (0.25, 0.35)  # apuesta pequeña
            elif board_texture == "wet":
                # Regla #4
                return (0.55, 0.80)  # apuesta grande
            else:
                # Tablero neutral → tamaño intermedio
                return (0.40, 0.60)
    elif street == "turn":
        # Regla #7 sugiere al menos 66% si es segunda barrel
        return (0.66, 1.00)
    elif street == "river":
        # En river, depende de si tu rango está polarizado (Regla #6) u
        # objetivo de control de bote/fold equity
        return (0.50, 1.00)
    else:
        return (0.0, 0.0)


# Ejemplos de uso de las funciones:
# pct_utg, utg_hands = get_open_range("UTG")
# pct_bb_vs_ep, bb_vs_ep_hands = get_call_range("BB_vs_EP")
# bet_size_range = suggest_bet_size(board_texture="dry", street="flop", in_3bet_pot=False)
# print(f"Apostar entre {bet_size_range[0]*100:.0f}% y {bet_size_range[1]*100:.0f}% del bote")


# ———————————————————————————————————————————————
# FIN DE rangos.py
# ———————————————————————————————————————————————
