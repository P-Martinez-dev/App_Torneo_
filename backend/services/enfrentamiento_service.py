from repositories import partido_repository, jugador_repository, peleador_repository, torneo_repository


class JugadorNoEncontradoError(Exception):
    pass


class EnfrentamientoInvalidoError(Exception):
    pass


def obtener_enfrentamiento(jugador_a_id: int, jugador_b_id: int) -> dict:
    """Historial completo entre dos jugadores, visto desde el lado de A.

    No hay query propia a propósito: sale de obtener_finalizados_por_jugador
    (la misma que usa el perfil), filtrando los partidos donde el rival es
    B. Así el récord de acá coincide SIEMPRE con el de 'rivales' del
    perfil -- mismo criterio (sin repechaje/desempate), misma fuente, sin
    dos queries que puedan desincronizarse el día que se cambie una.

    Todo se devuelve orientado a A/B (y no a jugador1/jugador2 del
    partido): quién quedó como jugador1 depende de cómo se armó el fixture,
    y para leer un cara a cara eso es ruido."""
    if jugador_a_id == jugador_b_id:
        raise EnfrentamientoInvalidoError("Elegí dos jugadores distintos")

    jugadores = {j.id: j for j in jugador_repository.obtener_todos()}
    for jid in (jugador_a_id, jugador_b_id):
        if jid not in jugadores:
            raise JugadorNoEncontradoError(f"No existe el jugador {jid}")

    partidos = [
        p for p in partido_repository.obtener_finalizados_por_jugador(jugador_a_id)
        if jugador_b_id in (p.jugador1_id, p.jugador2_id)
    ]
    # Todos los torneos de A, cualquier estado: un partido ya finalizado de
    # un torneo que sigue en curso también cuenta (igual que en el perfil).
    torneos_por_id = {t.id: t for t in torneo_repository.obtener_todos_de_jugador(jugador_a_id)}
    nombres_peleador = {pl.id: pl.nombre for pl in peleador_repository.obtener_todos()}

    return {
        "jugador_a": _datos_jugador(jugadores[jugador_a_id]),
        "jugador_b": _datos_jugador(jugadores[jugador_b_id]),
        "resumen": _resumen(jugador_a_id, partidos),
        "torneos": _historial_por_torneo(jugador_a_id, partidos, torneos_por_id, nombres_peleador),
        "evolucion": _evolucion(jugador_a_id, partidos, torneos_por_id),
    }


def _evolucion(jugador_a_id, partidos, torneos_por_id):
    """Victorias ACUMULADAS de cada uno después de cada partido entre ellos,
    en orden cronológico: la serie del gráfico de evolución del cara a cara
    (partido 1, 2, 3... en el eje horizontal). El último punto coincide
    siempre con el récord del resumen, porque sale de los mismos partidos.

    Cada punto trae además de qué partido se trata, para el detalle que
    aparece al pasar el mouse."""
    acumulado_a = acumulado_b = 0
    puntos = []
    for i, p in enumerate(partidos, start=1):
        gano_a = p.ganador_id == jugador_a_id
        if gano_a:
            acumulado_a += 1
        else:
            acumulado_b += 1
        torneo = torneos_por_id.get(p.torneo_id)
        puntos.append({
            "n": i,
            "torneo_id": p.torneo_id,
            "torneo_nombre": torneo.nombre if torneo else None,
            "fase": p.fase,
            "ronda": p.ronda,
            "jornada": p.jornada,
            "gano_a": gano_a,
            "acumulado_a": acumulado_a,
            "acumulado_b": acumulado_b,
        })
    return puntos


def _datos_jugador(jugador):
    return {
        "id": jugador.id,
        "nombre": jugador.nombre,
        "imagen_icono": jugador.imagen_icono_path,
    }


def _resumen(jugador_a_id, partidos):
    jugados = len(partidos)
    ganados_a = sum(1 for p in partidos if p.ganador_id == jugador_a_id)
    return {
        "partidos_jugados": jugados,
        "ganados_a": ganados_a,
        "ganados_b": jugados - ganados_a,
    }


def _historial_por_torneo(jugador_a_id, partidos, torneos_por_id, nombres_peleador):
    """Agrupa por torneo respetando el orden que ya traen los partidos
    (fecha del torneo + orden interno): como vienen ordenados, alcanza con
    abrir un grupo nuevo cada vez que cambia el torneo_id.

    Queda en orden cronológico (más viejo primero), igual que el resto de
    las estadísticas -- cómo se MUESTRA (ej: más reciente arriba) lo decide
    la plantilla, y así lo que se sume después (rachas, forma reciente) ya
    tiene los datos en el orden que necesita."""
    grupos = []
    for p in partidos:
        if not grupos or grupos[-1]["torneo_id"] != p.torneo_id:
            torneo = torneos_por_id.get(p.torneo_id)
            grupos.append({
                "torneo_id": p.torneo_id,
                "torneo_nombre": torneo.nombre if torneo else None,
                "fecha": torneo.fecha.isoformat() if torneo and torneo.fecha else None,
                "modo": torneo.modo if torneo else None,
                "ganados_a": 0,
                "ganados_b": 0,
                "partidos": [],
            })
        grupo = grupos[-1]

        a_es_jugador1 = p.jugador1_id == jugador_a_id
        peleador_a_id = p.jugador1_peleador_id if a_es_jugador1 else p.jugador2_peleador_id
        peleador_b_id = p.jugador2_peleador_id if a_es_jugador1 else p.jugador1_peleador_id
        gano_a = p.ganador_id == jugador_a_id

        if gano_a:
            grupo["ganados_a"] += 1
        else:
            grupo["ganados_b"] += 1

        grupo["partidos"].append({
            "partido_id": p.id,
            "fase": p.fase,
            "ronda": p.ronda,
            "jornada": p.jornada,
            # Si no se cargó peleador en ese partido quedan en None y la
            # plantilla muestra un guion.
            "peleador_a": nombres_peleador.get(peleador_a_id),
            "peleador_b": nombres_peleador.get(peleador_b_id),
            "gano_a": gano_a,
        })
    return grupos
