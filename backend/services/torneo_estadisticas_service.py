from repositories import partido_repository, jugador_repository, peleador_repository, torneo_repository
from services import estadisticas_config_service


class TorneoNoEncontradoError(Exception):
    pass


def _todos_los_maximos(lista, key):
    """Mismo criterio que en estadisticas_service: devuelve TODOS los que
    empatan en el máximo, no solo uno."""
    if not lista:
        return []
    m = max(key(f) for f in lista)
    return [f for f in lista if key(f) == m]


def obtener_estadisticas_torneo(torneo_id: int) -> dict:
    torneo = torneo_repository.obtener_por_id(torneo_id)
    if torneo is None:
        raise TorneoNoEncontradoError(f"No existe el torneo {torneo_id}")

    partidos = partido_repository.obtener_por_torneo(torneo_id)  # ordenados por 'orden' ASC
    finalizados = [p for p in partidos if p.estado == "finalizado"]

    nombres = {j.id: j.nombre for j in jugador_repository.obtener_todos()}
    nombres_peleador = {p.id: p.nombre for p in peleador_repository.obtener_todos()}

    jugadores_ids = set()
    for p in partidos:
        jugadores_ids.add(p.jugador1_id)
        jugadores_ids.add(p.jugador2_id)

    resultado = {
        "torneo_id": torneo_id,
        "cantidad_jugadores": len(jugadores_ids),
        "partidos_jugados": len(finalizados),
        "rounds": _stats_rounds(finalizados),
        "instancias_especiales": _instancias_especiales(torneo, finalizados),
        "partido_mas_renido": _partido_mas_renido(finalizados, nombres),
        "mas_tiempo_en_cancha": _mas_tiempo_en_cancha(torneo, finalizados, nombres),
        "mas_victorias": _mas_victorias(finalizados, nombres),
        "peleador_mas_usado": _peleador_mas_usado(torneo, finalizados, nombres_peleador),
        "rival_mas_diverso": _rival_mas_diverso(torneo, finalizados, nombres),
    }
    return estadisticas_config_service.filtrar_visibles(
        resultado, "torneo", campos_lista=("mas_victorias", "peleador_mas_usado", "rival_mas_diverso")
    )


def _stats_rounds(partidos):
    barridas = sum(1 for p in partidos if p.rondas_jugadas == 2)
    cerrados = sum(1 for p in partidos if p.rondas_jugadas == 3)
    return {
        "barridas": barridas,
        "cerrados": cerrados,
        "partidos_con_datos_de_rondas": barridas + cerrados,
    }


def _instancias_especiales(torneo, partidos):
    """Cuenta MINI-GRUPOS distintos (no partidos sueltos) -- un desempate
    de 3 jugadores con 3 partidos adentro es 1 instancia, no 3."""
    if torneo.modo != "grupos_eliminacion":
        return None
    desempates = len({p.grupo_id for p in partidos if p.fase == "desempate"})
    repechajes = len({p.grupo_id for p in partidos if p.fase == "repechaje"})
    return {"desempates_internos": desempates, "repechajes_cruzados": repechajes}


def _partido_mas_renido(partidos, nombres):
    """El criterio es cuántas veces se enfrentó el mismo par de jugadores
    en TODO el torneo (puede pasar por la cola de rey_de_la_cancha, o por un
    repechaje/desempate en grupos_eliminacion -- pero esos dos últimos no
    cuentan, porque no fueron partidos 'de verdad' del torneo, fueron
    para resolver un empate). Si el máximo es 1 (todos se cruzaron una
    sola vez), no hay 'más reñido' que marcar."""
    partidos_reales = [p for p in partidos if p.fase not in ("repechaje", "desempate")]
    conteo = {}
    for p in partidos_reales:
        clave = frozenset({p.jugador1_id, p.jugador2_id})
        conteo[clave] = conteo.get(clave, 0) + 1

    if not conteo or max(conteo.values()) <= 1:
        return {"hubo": False}

    maximo = max(conteo.values())
    parejas = [
        {"jugadores": sorted(nombres.get(j, "?") for j in clave), "veces": veces}
        for clave, veces in conteo.items() if veces == maximo
    ]
    return {"hubo": True, "veces": maximo, "parejas": parejas}


def _mas_tiempo_en_cancha(torneo, partidos, nombres):
    """Solo rey_de_la_cancha: la racha de victorias consecutivas más larga de
    un jugador EN UN SOLO TURNO en cancha (se corta apenas pierde, aunque
    después vuelva a entrar más tarde). No necesariamente es el campeón."""
    if torneo.modo != "rey_de_la_cancha":
        return None

    racha_actual, mejor_racha = {}, {}
    for p in partidos:
        ganador = p.ganador_id
        perdedor = p.jugador2_id if ganador == p.jugador1_id else p.jugador1_id
        racha_actual[ganador] = racha_actual.get(ganador, 0) + 1
        mejor_racha[ganador] = max(mejor_racha.get(ganador, 0), racha_actual[ganador])
        racha_actual[perdedor] = 0

    if not mejor_racha:
        return {"jugadores": [], "racha": 0}

    maximo = max(mejor_racha.values())
    jugadores = [nombres.get(jid) for jid, r in mejor_racha.items() if r == maximo]
    return {"jugadores": jugadores, "racha": maximo}


def _mas_victorias(partidos, nombres):
    conteo = {}
    for p in partidos:
        conteo[p.ganador_id] = conteo.get(p.ganador_id, 0) + 1
    lista = [{"jugador_id": jid, "nombre": nombres.get(jid), "victorias": v} for jid, v in conteo.items()]
    return _todos_los_maximos(lista, key=lambda f: f["victorias"])


def _peleador_mas_usado(torneo, partidos, nombres_peleador):
    """Excluye rey_de_la_cancha -- no se trackea peleador en ese modo (mismo
    criterio que las estadísticas de jugador)."""
    if torneo.modo == "rey_de_la_cancha":
        return []
    conteo = {}
    for p in partidos:
        for peleador_id in (p.jugador1_peleador_id, p.jugador2_peleador_id):
            if peleador_id is not None:
                conteo[peleador_id] = conteo.get(peleador_id, 0) + 1
    lista = [
        {"peleador_id": pid, "nombre": nombres_peleador.get(pid), "veces": v}
        for pid, v in conteo.items()
    ]
    return _todos_los_maximos(lista, key=lambda f: f["veces"])


def _rival_mas_diverso(torneo, partidos, nombres):
    """Cantidad de rivales DISTINTOS enfrentados, no cantidad de partidos
    -- el espejo de 'partido más reñido' (que mide repetición, esto mide
    variedad). No aplica a todos_contra_todos: ahí cada jugador se
    enfrenta exactamente una vez con cada rival por diseño (round-robin),
    así que 'quién enfrentó más rivales distintos' siempre da un empate
    trivial entre todos -- no dice nada de ese torneo puntual."""
    if torneo.modo == "todos_contra_todos":
        return None

    rivales_por_jugador = {}
    for p in partidos:
        rivales_por_jugador.setdefault(p.jugador1_id, set()).add(p.jugador2_id)
        rivales_por_jugador.setdefault(p.jugador2_id, set()).add(p.jugador1_id)

    lista = [
        {"jugador_id": jid, "nombre": nombres.get(jid), "rivales_distintos": len(rivales)}
        for jid, rivales in rivales_por_jugador.items()
    ]
    return _todos_los_maximos(lista, key=lambda f: f["rivales_distintos"])
