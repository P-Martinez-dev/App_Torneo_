from repositories import torneo_repository, partido_repository, jugador_repository, peleador_repository
from services import estadisticas_config_service

TOP_N = 5


def _top_n_con_empates(lista, key, n=TOP_N):
    """Mismo criterio usado en el resto del proyecto: primeros N valores
    DISTINTOS de key, con todos los empates incluidos (nunca se decide
    arbitrariamente cuál va primero si dan exactamente igual)."""
    ordenados = sorted(lista, key=lambda item: -key(item))
    valores_vistos = []
    resultado = []
    for item in ordenados:
        v = key(item)
        if v not in valores_vistos:
            if len(valores_vistos) >= n:
                break
            valores_vistos.append(v)
        resultado.append(item)
    return resultado


def obtener_estadisticas_peleador(peleador_id):
    """
    Estadísticas de un peleador puntual, mirando TODOS los partidos
    reales del historial (excluye repechaje/desempate, mismo criterio
    que el resto del proyecto) donde alguien lo usó, sin importar quién.
    """
    torneos = torneo_repository.obtener_finalizados()
    partidos = partido_repository.obtener_finalizados_por_torneos([t.id for t in torneos])

    nombres_jugador = {j.id: j.nombre for j in jugador_repository.obtener_todos()}
    nombres_peleador = {p.id: p.nombre for p in peleador_repository.obtener_todos()}

    # Cada vez que este peleador fue usado, de cualquiera de los dos lados
    apariciones = []
    lados = (
        ("jugador1_peleador_id", "jugador1_id", "jugador2_id", "jugador2_peleador_id"),
        ("jugador2_peleador_id", "jugador2_id", "jugador1_id", "jugador1_peleador_id"),
    )
    for p in partidos:
        for campo_peleador, campo_jugador, campo_rival, campo_peleador_rival in lados:
            if getattr(p, campo_peleador) != peleador_id:
                continue
            jugador_id = getattr(p, campo_jugador)
            apariciones.append({
                "jugador_id": jugador_id,
                "rival_jugador_id": getattr(p, campo_rival),
                "rival_peleador_id": getattr(p, campo_peleador_rival),
                "gano": p.ganador_id == jugador_id,
                # Contexto extra para las estadísticas de abajo: las rondas
                # dicen si fue barrida o partido cerrado, y el torneo/fecha
                # permiten ver si el peleador es recurrente o fue de una noche.
                "rondas": p.rondas_jugadas,
                "torneo_id": p.torneo_id,
                "fecha": p.fecha_jugado,
                "orden": p.orden,
            })

    veces_usado = len(apariciones)
    victorias = sum(1 for a in apariciones if a["gano"])
    win_rate = round(victorias / veces_usado, 3) if veces_usado else 0

    conteo_uso_por_jugador = {}
    victorias_vs_peleador = {}
    derrotas_vs_peleador = {}
    derrotas_vs_jugador = {}
    partidos_vs_jugador = {}

    for a in apariciones:
        conteo_uso_por_jugador[a["jugador_id"]] = conteo_uso_por_jugador.get(a["jugador_id"], 0) + 1
        partidos_vs_jugador[a["rival_jugador_id"]] = partidos_vs_jugador.get(a["rival_jugador_id"], 0) + 1
        if not a["gano"]:
            derrotas_vs_jugador[a["rival_jugador_id"]] = derrotas_vs_jugador.get(a["rival_jugador_id"], 0) + 1
        if a["rival_peleador_id"] is not None:
            destino = victorias_vs_peleador if a["gano"] else derrotas_vs_peleador
            destino[a["rival_peleador_id"]] = destino.get(a["rival_peleador_id"], 0) + 1

    # --- Estadísticas nuevas ---

    # Barridas: partidos ganados o perdidos 2-0. Distingue al peleador que
    # arrasa del que gana peleado. Solo cuentan los partidos donde se cargó
    # el dato de rondas (es opcional al cargar el resultado).
    con_rondas = [a for a in apariciones if a["rondas"]]
    barridas_a_favor = sum(1 for a in con_rondas if a["gano"] and a["rondas"] == 2)
    barridas_en_contra = sum(1 for a in con_rondas if not a["gano"] and a["rondas"] == 2)
    partidos_cerrados = sum(1 for a in con_rondas if a["rondas"] == 3)

    # En cuántos torneos distintos apareció: es otra cosa que "veces usado".
    # Un peleador con 20 usos en un solo torneo fue el capricho de una noche;
    # con 20 usos repartidos en 10 torneos, es parte del repertorio del grupo.
    torneos_distintos = len({a["torneo_id"] for a in apariciones})

    # Primera y última vez que se usó: sirve para ver si está de moda o si
    # cayó en desuso hace rato.
    fechas = sorted(a["fecha"] for a in apariciones if a["fecha"])
    primera_vez = fechas[0].isoformat() if fechas else None
    ultima_vez = fechas[-1].isoformat() if fechas else None

    # Espejos: partidos donde los DOS jugadores eligieron este peleador.
    # Se divide por 2 porque cada uno de esos partidos genera dos apariciones
    # (una por lado), y lo que se quiere contar son partidos, no apariciones.
    espejos = sum(1 for a in apariciones if a["rival_peleador_id"] == peleador_id) // 2

    # Racha más larga de victorias, en orden cronológico. Se ordena por fecha
    # y, dentro del mismo torneo, por el orden en que se jugaron.
    en_orden = sorted(apariciones, key=lambda a: (a["fecha"] or "", a["orden"] or 0))
    racha_actual = 0
    mejor_racha = 0
    for a in en_orden:
        racha_actual = racha_actual + 1 if a["gano"] else 0
        mejor_racha = max(mejor_racha, racha_actual)

    # Peor enemigo: contra qué peleador tiene el PEOR win rate. Es distinto
    # de "con quién perdió más", que cuenta cantidad: perder 3 de 3 es peor
    # que perder 5 de 20, aunque el número absoluto diga lo contrario. Se
    # pide un mínimo de enfrentamientos para que un 0-1 suelto no gane.
    MIN_ENFRENTAMIENTOS = 3
    enfrentamientos = {}
    for a in apariciones:
        rival = a["rival_peleador_id"]
        if rival is None:
            continue
        d = enfrentamientos.setdefault(rival, {"jugados": 0, "ganados": 0})
        d["jugados"] += 1
        if a["gano"]:
            d["ganados"] += 1
    candidatos_enemigo = [
        {"peleador_id": pid, "nombre": nombres_peleador.get(pid),
         "jugados": d["jugados"], "ganados": d["ganados"],
         "win_rate": round(d["ganados"] / d["jugados"], 3)}
        for pid, d in enfrentamientos.items()
        if d["jugados"] >= MIN_ENFRENTAMIENTOS
    ]
    peor_enemigo = _top_n_con_empates(
        candidatos_enemigo, key=lambda f: -f["win_rate"], n=3
    ) if candidatos_enemigo else []

    # Mejor resultado logrado: el mejor puesto que sacó un jugador en un
    # torneo donde usó este peleador. Sale de la tabla general, que ya tiene
    # el puesto de cada jugador en cada torneo y está cacheada.
    mejor_resultado = _mejor_resultado(apariciones)

    def _lista_jugadores(conteo):
        return [{"jugador_id": jid, "nombre": nombres_jugador.get(jid), "veces": c} for jid, c in conteo.items()]

    def _lista_peleadores(conteo):
        return [{"peleador_id": pid, "nombre": nombres_peleador.get(pid), "veces": c} for pid, c in conteo.items()]

    resultado = {
        "peleador_id": peleador_id,
        "veces_usado": veces_usado,
        "win_rate": win_rate,
        "mas_usado_por": _top_n_con_empates(_lista_jugadores(conteo_uso_por_jugador), key=lambda f: f["veces"]),
        "a_quien_le_gano_mas": _top_n_con_empates(_lista_peleadores(victorias_vs_peleador), key=lambda f: f["veces"]),
        "con_quien_perdio_mas": _top_n_con_empates(_lista_peleadores(derrotas_vs_peleador), key=lambda f: f["veces"]),
        "contra_quien_perdio_mas": _top_n_con_empates(_lista_jugadores(derrotas_vs_jugador), key=lambda f: f["veces"]),
        "contra_quien_jugo_mas": _top_n_con_empates(_lista_jugadores(partidos_vs_jugador), key=lambda f: f["veces"]),
        "barridas_a_favor": barridas_a_favor,
        "barridas_en_contra": barridas_en_contra,
        "partidos_cerrados": partidos_cerrados,
        "torneos_distintos": torneos_distintos,
        "primera_vez": primera_vez,
        "ultima_vez": ultima_vez,
        "espejos": espejos,
        "mejor_racha": mejor_racha,
        "peor_enemigo": peor_enemigo,
        "mejor_resultado": mejor_resultado,
    }
    return estadisticas_config_service.filtrar_visibles(
        resultado, "peleador",
        campos_lista=("mas_usado_por", "a_quien_le_gano_mas", "con_quien_perdio_mas",
                      "contra_quien_perdio_mas", "contra_quien_jugo_mas", "peor_enemigo",
                      "mejor_resultado"),
    )


def _mejor_resultado(apariciones):
    """El mejor puesto que sacó un jugador en un torneo donde usó este
    peleador. Devuelve lista (puede haber empates en el mejor puesto).

    El puesto de cada jugador en cada torneo ya está calculado dentro de la
    tabla general (en sus insignias), que además está cacheada: se busca ahí
    en vez de recalcularlo, que costaría varias consultas por torneo.
    """
    if not apariciones:
        return []

    from services import cache_resultados, tabla_general_service
    tabla = cache_resultados.obtener("tabla-general:[]", tabla_general_service.calcular_tabla_general)

    # {(jugador_id, torneo_id): puesto}
    puesto_por = {}
    for fila in tabla:
        for ins in fila.get("insignias", []):
            puesto_por[(fila["jugador_id"], ins["torneo_id"])] = (ins["puesto"], ins["torneo_nombre"], fila["nombre"])

    resultados = []
    vistos = set()
    for a in apariciones:
        clave = (a["jugador_id"], a["torneo_id"])
        if clave in vistos:
            continue
        vistos.add(clave)
        dato = puesto_por.get(clave)
        if dato is None:
            continue
        puesto, torneo_nombre, jugador_nombre = dato
        resultados.append({
            "puesto": puesto,
            "torneo_id": a["torneo_id"],
            "torneo_nombre": torneo_nombre,
            "nombre": jugador_nombre,
        })

    if not resultados:
        return []
    mejor = min(r["puesto"] for r in resultados)
    return [r for r in resultados if r["puesto"] == mejor]
