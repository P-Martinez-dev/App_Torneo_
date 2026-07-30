from repositories import partido_repository, torneo_jugador_repository, grupo_repository


def detectar_bloque_en_riesgo(tabla, n_directos):
    """
    Chequea si hay empate de puntos justo en la línea de corte de
    clasificación directa de un grupo. Si lo hay, devuelve el bloque
    completo de jugadores empatados en ese puntaje (no solo el de la
    frontera) y cuántos cupos le corresponden a ese bloque.
    Devuelve None si no hay empate en el corte (nada que resolver).
    """
    if n_directos <= 0 or n_directos >= len(tabla):
        return None

    punto_corte = tabla[n_directos - 1]["puntos"]
    if tabla[n_directos]["puntos"] != punto_corte:
        return None

    bloque = [f for f in tabla if f["puntos"] == punto_corte]
    ya_clasificados = sum(1 for f in tabla if f["puntos"] > punto_corte)
    slots_para_bloque = n_directos - ya_clasificados
    return bloque, slots_para_bloque


def resolver_por_enfrentamiento_directo(grupo_id, bloque):
    """
    Intenta desempatar un bloque de jugadores empatados en puntos usando
    solo los resultados que ya jugaron entre ellos (en todos-contra-todos ya
    se cruzaron). Devuelve el bloque reordenado (mejor primero) si el
    head-to-head alcanza para desempatar sin ambigüedad, o None si queda un
    ciclo real (ej. A le ganó a B, B a C, C a A) que necesita intervención
    del admin vía mini-grupo de desempate.
    """
    ids_bloque = {f["torneo_jugador_id"] for f in bloque}
    id_por_jugador = {f["jugador_id"]: f["torneo_jugador_id"] for f in bloque}

    partidos = partido_repository.obtener_finalizados_por_grupo(grupo_id, [])
    puntos_h2h = {tj_id: 0 for tj_id in ids_bloque}
    for p in partidos:
        ganador_tj = id_por_jugador.get(p.ganador_id)
        perdedor_id = p.jugador2_id if p.ganador_id == p.jugador1_id else p.jugador1_id
        perdedor_tj = id_por_jugador.get(perdedor_id)
        if ganador_tj in ids_bloque and perdedor_tj in ids_bloque:
            puntos_h2h[ganador_tj] += 1

    conteos = list(puntos_h2h.values())
    if len(set(conteos)) != len(conteos):
        # Dos o más quedaron con el mismo puntaje entre ellos -> no hay
        # orden lineal claro (ciclo, o bloque de 4+ con sub-empate).
        return None

    orden_ids = sorted(puntos_h2h, key=lambda tj_id: puntos_h2h[tj_id], reverse=True)
    por_id = {f["torneo_jugador_id"]: f for f in bloque}
    return [por_id[tj_id] for tj_id in orden_ids]


def calcular_tabla_grupo(grupo_id, partidos_excluidos_ids=None):
    """
    Tabla de posiciones de un grupo. Sin criterio de desempate (definido
    a propósito): si dos jugadores quedan con los mismos puntos, quedan
    en el mismo orden relativo hasta que se resuelva por repechaje o forzado.
    """
    partidos_excluidos_ids = partidos_excluidos_ids or []
    jugadores = torneo_jugador_repository.obtener_jugadores_de_grupo(grupo_id)
    partidos = partido_repository.obtener_finalizados_por_grupo(grupo_id, partidos_excluidos_ids)

    tabla = {
        j["torneo_jugador_id"]: {
            "torneo_jugador_id": j["torneo_jugador_id"],
            "jugador_id": j["jugador_id"],
            "nombre": j["nombre"],
            "pj": 0, "pg": 0, "pp": 0, "puntos": 0,
        }
        for j in jugadores
    }

    id_por_jugador = {j["jugador_id"]: j["torneo_jugador_id"] for j in jugadores}

    for partido in partidos:
        ganador_tj = id_por_jugador.get(partido.ganador_id)
        perdedor_id = (
            partido.jugador2_id if partido.ganador_id == partido.jugador1_id
            else partido.jugador1_id
        )
        perdedor_tj = id_por_jugador.get(perdedor_id)

        if ganador_tj in tabla:
            tabla[ganador_tj]["pj"] += 1
            tabla[ganador_tj]["pg"] += 1
            tabla[ganador_tj]["puntos"] += 1
        if perdedor_tj in tabla:
            tabla[perdedor_tj]["pj"] += 1
            tabla[perdedor_tj]["pp"] += 1

    return sorted(tabla.values(), key=lambda f: f["puntos"], reverse=True)


def calcular_tabla_todos_contra_todos(torneo_id, partidos_excluidos_ids=None):
    """Misma lógica que calcular_tabla_grupo, pero sin filtrar por grupo."""
    partidos_excluidos_ids = partidos_excluidos_ids or []
    jugadores = torneo_jugador_repository.obtener_jugadores_de_torneo(torneo_id)
    partidos = partido_repository.obtener_finalizados_por_torneo(
        torneo_id, "todos_contra_todos", partidos_excluidos_ids
    )

    tabla = {
        j["torneo_jugador_id"]: {
            "torneo_jugador_id": j["torneo_jugador_id"],
            "jugador_id": j["jugador_id"],
            "nombre": j["nombre"],
            "pj": 0, "pg": 0, "pp": 0, "puntos": 0,
        }
        for j in jugadores
    }
    id_por_jugador = {j["jugador_id"]: j["torneo_jugador_id"] for j in jugadores}

    for partido in partidos:
        ganador_tj = id_por_jugador.get(partido.ganador_id)
        perdedor_id = (
            partido.jugador2_id if partido.ganador_id == partido.jugador1_id
            else partido.jugador1_id
        )
        perdedor_tj = id_por_jugador.get(perdedor_id)

        tabla[ganador_tj]["pj"] += 1
        tabla[ganador_tj]["pg"] += 1
        tabla[ganador_tj]["puntos"] += 1
        tabla[perdedor_tj]["pj"] += 1
        tabla[perdedor_tj]["pp"] += 1

    return sorted(tabla.values(), key=lambda f: f["puntos"], reverse=True)


def _posicion_resuelta_en_grupo_origen(grupo_origen_id, jugador_id, tabla_origen):
    """
    Posición de un jugador en su grupo original, resolviendo primero
    cualquier empate en el corte (igual que hace calcular_clasificados):
    por head-to-head si alcanza, o por el mini-grupo de desempate si hubo
    un ciclo real. Sin esto, un candidato a repechaje que venía de un
    empate interno mostraría una posición ambigua/arbitraria (la tabla
    cruda no tiene forma de ordenar a los empatados).
    """
    fila = next((f for f in tabla_origen if f["jugador_id"] == jugador_id), None)
    if fila is None:
        return None, None

    posicion_cruda = tabla_origen.index(fila) + 1
    puntos = fila["puntos"]
    bloque_empatado = [f for f in tabla_origen if f["puntos"] == puntos]
    if len(bloque_empatado) == 1:
        return posicion_cruda, fila

    ya_arriba = sum(1 for f in tabla_origen if f["puntos"] > puntos)
    orden_h2h = resolver_por_enfrentamiento_directo(grupo_origen_id, bloque_empatado)
    if orden_h2h is not None:
        idx = next(i for i, f in enumerate(orden_h2h) if f["jugador_id"] == jugador_id)
        return ya_arriba + idx + 1, fila

    hijo = grupo_repository.obtener_desempate_interno(grupo_origen_id)
    if hijo is not None:
        tabla_hijo = calcular_tabla_grupo(hijo.id)
        idx = next((i for i, f in enumerate(tabla_hijo) if f["jugador_id"] == jugador_id), None)
        if idx is not None:
            return ya_arriba + idx + 1, fila

    return None, fila  # ciclo real todavía sin resolver -- no hay posición firme que mostrar


def contexto_repechaje(torneo_id, grupo_repechaje_id):
    """
    Arma un resumen por jugador del repechaje: de qué grupo original viene,
    en qué posición quedó ahí, y cómo va dentro del propio repechaje.
    Es informativo -- no decide nada, es la 'sugerencia' para el forzado.
    """
    jugadores_repechaje = torneo_jugador_repository.obtener_jugadores_de_grupo(grupo_repechaje_id)
    tabla_repechaje = calcular_tabla_grupo(grupo_repechaje_id)
    posicion_en_repechaje = {
        f["jugador_id"]: i for i, f in enumerate(tabla_repechaje, start=1)
    }

    contexto = []
    for j in jugadores_repechaje:
        grupo_origen = torneo_jugador_repository.obtener_grupo_original(torneo_id, j["jugador_id"])
        tabla_origen = calcular_tabla_grupo(grupo_origen["id"]) if grupo_origen else []
        posicion_origen, fila_origen = (
            _posicion_resuelta_en_grupo_origen(grupo_origen["id"], j["jugador_id"], tabla_origen)
            if grupo_origen else (None, None)
        )

        contexto.append({
            "jugador_id": j["jugador_id"],
            "nombre": j["nombre"],
            "grupo_origen": grupo_origen["nombre"] if grupo_origen else None,
            "posicion_grupo_origen": posicion_origen,
            "estadisticas_grupo_origen": fila_origen,
            "posicion_actual_repechaje": posicion_en_repechaje.get(j["jugador_id"]),
            "estadisticas_repechaje": next(
                (f for f in tabla_repechaje if f["jugador_id"] == j["jugador_id"]), None
            ),
        })

    return contexto