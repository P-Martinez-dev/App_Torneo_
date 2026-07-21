from repositories import partido_repository, torneo_jugador_repository


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
        fila_origen = next(
            (f for f in tabla_origen if f["jugador_id"] == j["jugador_id"]), None
        )
        posicion_origen = (
            tabla_origen.index(fila_origen) + 1 if fila_origen else None
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