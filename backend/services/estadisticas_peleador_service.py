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
    }
    return estadisticas_config_service.filtrar_visibles(
        resultado, "peleador",
        campos_lista=("mas_usado_por", "a_quien_le_gano_mas", "con_quien_perdio_mas", "contra_quien_perdio_mas", "contra_quien_jugo_mas"),
    )
