from repositories import config_estadistica_repository

# Registro central de TODAS las estadísticas que se pueden apagar,
# agrupadas por categoría. Cada 'clave' tiene que coincidir exactamente
# con el nombre del campo que devuelve el service correspondiente (ver
# _filtrar_visibles en cada uno) -- si se agrega una estadística nueva
# en el futuro, hay que sumarla acá también para que aparezca en la
# pantalla de admin.
REGISTRO = [
    # --- Torneo puntual ---
    {"clave": "torneo.rounds", "etiqueta": "Barridas vs. cerrados", "categoria": "Torneo"},
    {"clave": "torneo.instancias_especiales", "etiqueta": "Instancias especiales (desempates/repechajes)", "categoria": "Torneo"},
    {"clave": "torneo.partido_mas_renido", "etiqueta": "Partido más reñido", "categoria": "Torneo"},
    {"clave": "torneo.mas_tiempo_en_cancha", "etiqueta": "Más tiempo en cancha (rey de la cancha)", "categoria": "Torneo"},
    {"clave": "torneo.mas_victorias", "etiqueta": "Más victorias en el torneo", "categoria": "Torneo"},
    {"clave": "torneo.peleador_mas_usado", "etiqueta": "Peleador más usado", "categoria": "Torneo"},
    {"clave": "torneo.rival_mas_diverso", "etiqueta": "Rival más diverso", "categoria": "Torneo"},

    # --- Jugador ---
    {"clave": "jugador.ultimos_resultados", "etiqueta": "Últimos resultados", "categoria": "Jugador"},
    {"clave": "jugador.rachas", "etiqueta": "Rachas", "categoria": "Jugador"},
    {"clave": "jugador.rivales.rival_mas_vencido", "etiqueta": "Rival más vencido", "categoria": "Jugador"},
    {"clave": "jugador.rivales.rival_mas_frecuente", "etiqueta": "Rival más frecuente", "categoria": "Jugador"},
    {"clave": "jugador.rivales.matchup_parejo", "etiqueta": "Matchup parejo", "categoria": "Jugador"},
    {"clave": "jugador.rivales.nemesis", "etiqueta": "Némesis", "categoria": "Jugador"},
    {"clave": "jugador.peleadores.mas_frecuente", "etiqueta": "Peleador más usado (propio)", "categoria": "Jugador"},
    {"clave": "jugador.peleadores.mejor_win_rate", "etiqueta": "Peleador con mejor win rate (propio)", "categoria": "Jugador"},
    {"clave": "jugador.peleadores.peor_win_rate", "etiqueta": "Peleador con peor win rate (propio)", "categoria": "Jugador"},
    {"clave": "jugador.peleadores_rivales.mas_frecuente", "etiqueta": "Peleador rival más frecuente", "categoria": "Jugador"},
    {"clave": "jugador.peleadores_rivales.que_te_gana_mas", "etiqueta": "Peleador que más te gana", "categoria": "Jugador"},
    {"clave": "jugador.peleadores_rivales.que_le_ganas_mas", "etiqueta": "Peleador al que más le ganás", "categoria": "Jugador"},
    {"clave": "jugador.torneos.torneos_jugados_por_modo", "etiqueta": "Torneos jugados por modo", "categoria": "Jugador"},
    {"clave": "jugador.torneos.veces_campeon", "etiqueta": "Veces campeón", "categoria": "Jugador"},
    {"clave": "jugador.torneos.mejor_puesto_historico", "etiqueta": "Mejor puesto histórico", "categoria": "Jugador"},
    {"clave": "jugador.torneos.promedio_puesto", "etiqueta": "Promedio de puesto", "categoria": "Jugador"},
    {"clave": "jugador.veces_en_repechaje_o_desempate", "etiqueta": "Veces en repechaje/desempate", "categoria": "Jugador"},
    {"clave": "jugador.rounds", "etiqueta": "Barridas vs. cerrados (propio)", "categoria": "Jugador"},
    {"clave": "jugador.rey_de_la_cancha.quien_te_elimino_mas", "etiqueta": "Quién te eliminó más (rey de la cancha)", "categoria": "Jugador"},
    {"clave": "jugador.rey_de_la_cancha.a_quien_eliminaste_mas", "etiqueta": "A quién eliminaste más (rey de la cancha)", "categoria": "Jugador"},
    {"clave": "jugador.mejores_victorias", "etiqueta": "Mejores victorias", "categoria": "Jugador"},
    {"clave": "jugador.peores_caidas", "etiqueta": "Peores caídas", "categoria": "Jugador"},

    # --- Peleador ---
    {"clave": "peleador.mas_usado_por", "etiqueta": "Más usado por", "categoria": "Peleador"},
    {"clave": "peleador.a_quien_le_gano_mas", "etiqueta": "A qué peleador le ganó más", "categoria": "Peleador"},
    {"clave": "peleador.con_quien_perdio_mas", "etiqueta": "Con qué peleador perdió más", "categoria": "Peleador"},
    {"clave": "peleador.contra_quien_perdio_mas", "etiqueta": "Contra qué jugador perdió más", "categoria": "Peleador"},
    {"clave": "peleador.contra_quien_jugo_mas", "etiqueta": "Contra qué jugador jugó más", "categoria": "Peleador"},

    # --- Generales ---
    {"clave": "generales.top_torneos_mas_jugadores", "etiqueta": "Torneos con más jugadores", "categoria": "Generales"},
    {"clave": "generales.top_torneos_mas_partidos", "etiqueta": "Torneos con más partidos", "categoria": "Generales"},
    {"clave": "generales.top_rivalidades_mas_frecuentes", "etiqueta": "Rivalidades más frecuentes", "categoria": "Generales"},
    {"clave": "generales.top_rivalidades_mas_parejas", "etiqueta": "Rivalidades más parejas", "categoria": "Generales"},
    {"clave": "generales.top_padreadas", "etiqueta": "Mayores \"padreadas\"", "categoria": "Generales"},
    {"clave": "generales.top_apariciones_podio", "etiqueta": "Más apariciones en podio", "categoria": "Generales"},
    {"clave": "generales.top_resultados_sorpresivos", "etiqueta": "Resultados más sorpresivos", "categoria": "Generales"},
    {"clave": "generales.distancia_rating_primero_ultimo", "etiqueta": "Distancia de rating (1° a último)", "categoria": "Generales"},
]


def obtener_registro_con_estado():
    """El registro completo, con el estado actual de cada una -- para la
    pantalla de admin."""
    ocultas = config_estadistica_repository.obtener_ocultas()
    return [{**item, "visible": item["clave"] not in ocultas} for item in REGISTRO]


def actualizar_visibilidad(clave, visible):
    claves_validas = {item["clave"] for item in REGISTRO}
    if clave not in claves_validas:
        raise ValueError(f"'{clave}' no es una estadística conocida")
    config_estadistica_repository.actualizar_visibilidad(clave, visible)


def filtrar_visibles(resultado, prefijo, campos_lista=()):
    """Recorre 'resultado' (un dict) y, para cada clave marcada como NO
    visible bajo ese prefijo, la vacía -- None para un campo simple, []
    para uno que la plantilla ya trata como lista (evita romper los
    '{% if %}' que ya existen en las plantillas, no hace falta tocarlas)."""
    from services import cache_resultados
    ocultas = cache_resultados.obtener("estadisticas-ocultas",
        config_estadistica_repository.obtener_ocultas)
    for campo in list(resultado.keys()):
        if f"{prefijo}.{campo}" in ocultas:
            resultado[campo] = [] if campo in campos_lista else None
    return resultado
