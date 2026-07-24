import random

from repositories import partido_repository, torneo_repository, grupo_repository, torneo_jugador_repository
from services import tabla_service


# =========================================================
# Generación de fixture inicial (según modo de torneo)
# =========================================================

def generar_fixture_inicial(torneo_id, modo, jugadores_ids,
                             cupos_eliminacion=None, cantidad_grupos=None):
    if modo == "todos_contra_todos":
        _generar_todos_contra_todos(torneo_id, jugadores_ids)
    elif modo == "grupos_eliminacion":
        _generar_grupos(torneo_id, jugadores_ids, cupos_eliminacion, cantidad_grupos)
    elif modo == "cinco_vidas":
        _generar_cinco_vidas(torneo_id, jugadores_ids)


def _fixture_round_robin(jugadores_ids):
    """
    Algoritmo del círculo: devuelve una lista de jornadas, cada una con
    una lista de (jugador1, jugador2). Si la cantidad es impar, se agrega
    un jugador 'fantasma' (None) — quien lo enfrenta descansa esa jornada.
    """
    jugadores = jugadores_ids.copy()
    if len(jugadores) % 2 != 0:
        jugadores.append(None)

    n = len(jugadores)
    jornadas = []
    for _ in range(n - 1):
        ronda = []
        for i in range(n // 2):
            j1, j2 = jugadores[i], jugadores[n - 1 - i]
            if j1 is not None and j2 is not None:
                ronda.append((j1, j2))
        jornadas.append(ronda)
        jugadores.insert(1, jugadores.pop())
    return jornadas


def _generar_todos_contra_todos(torneo_id, jugadores_ids):
    fixture = _fixture_round_robin(jugadores_ids)
    partidos_a_crear = []
    orden = 1
    for jornada, ronda in enumerate(fixture, start=1):
        for j1, j2 in ronda:
            partidos_a_crear.append({
                "torneo_id": torneo_id, "jugador1_id": j1, "jugador2_id": j2,
                "fase": "todos_contra_todos", "ronda": None, "jornada": jornada,
                "orden": orden, "grupo_id": None,
            })
            orden += 1
    partido_repository.crear_muchos(partidos_a_crear)


def _repartir_en_grupos(jugadores_ids, cantidad_grupos):
    """
    Reparte lo más parejo posible: si sobran jugadores al dividir,
    los primeros grupos reciben uno de más (ej: 13 jugadores / 3 grupos -> 4, 4, 5).
    """
    jugadores = jugadores_ids.copy()
    random.shuffle(jugadores)
    base = len(jugadores) // cantidad_grupos
    resto = len(jugadores) % cantidad_grupos

    grupos = []
    idx = 0
    for g in range(cantidad_grupos):
        tamaño = base + (1 if g < resto else 0)
        grupos.append(jugadores[idx: idx + tamaño])
        idx += tamaño
    return grupos


def _generar_grupos(torneo_id, jugadores_ids, cupos_eliminacion, cantidad_grupos):
    grupos_jugadores = _repartir_en_grupos(jugadores_ids, cantidad_grupos)

    grupo_ids = []
    for i, jugadores_del_grupo in enumerate(grupos_jugadores, start=1):
        grupo_id = grupo_repository.crear(torneo_id, nombre=f"Grupo {chr(64 + i)}", tipo="grupo")
        torneo_repository.asignar_jugadores_a_grupo(grupo_id, jugadores_del_grupo)
        grupo_ids.append(grupo_id)

    fixtures_por_grupo = {
        grupo_id: _fixture_round_robin(jugadores_del_grupo)
        for grupo_id, jugadores_del_grupo in zip(grupo_ids, grupos_jugadores)
    }
    # nota: grupo_ids ya son ints (devueltos por grupo_repository.crear), no objetos Grupo

    max_jornadas = max(len(f) for f in fixtures_por_grupo.values())
    partidos_a_crear = []
    orden = 1
    for jornada in range(max_jornadas):
        for grupo_id, fixture in fixtures_por_grupo.items():
            if jornada < len(fixture):
                for j1, j2 in fixture[jornada]:
                    partidos_a_crear.append({
                        "torneo_id": torneo_id, "jugador1_id": j1, "jugador2_id": j2,
                        "fase": "grupos", "ronda": None, "jornada": jornada + 1,
                        "orden": orden, "grupo_id": grupo_id,
                    })
                    orden += 1

    partido_repository.crear_muchos(partidos_a_crear)


def _generar_cinco_vidas(torneo_id, jugadores_ids, orden_aleatorio=True):
    orden = jugadores_ids.copy()
    if orden_aleatorio:
        random.shuffle(orden)

    torneo_repository.inicializar_cola_cinco_vidas(torneo_id, orden)

    partido_repository.crear_muchos([{
        "torneo_id": torneo_id, "jugador1_id": orden[0], "jugador2_id": orden[1],
        "fase": "cinco_vidas", "ronda": None, "jornada": None, "orden": 1,
        "grupo_id": None,
    }])


# =========================================================
# Avance del torneo (pantalla fullscreen)
# =========================================================

def obtener_partido_actual(torneo_id):
    partido = partido_repository.obtener_en_curso(torneo_id)
    if partido is None:
        partido = partido_repository.obtener_proximo_pendiente(torneo_id)
        if partido is not None:
            partido_repository.marcar_en_curso(partido.id)
    return partido.to_dict() if partido else None


def listar_partidos_pendientes(torneo_id):
    partidos = partido_repository.obtener_pendientes_y_pospuestos(torneo_id)
    return [p.to_dict() for p in partidos]


def seleccionar_partido_actual(torneo_id, partido_id):
    """Navegar a otro enfrentamiento. El que estaba en curso queda pospuesto."""
    actual = partido_repository.obtener_en_curso(torneo_id)
    if actual is not None and actual.id != partido_id:
        partido_repository.marcar_pospuesto(actual.id)
    partido_repository.marcar_en_curso(partido_id)
    return partido_repository.obtener_por_id(partido_id).to_dict()


class ResultadoInvalidoError(Exception):
    pass


def cargar_resultado(partido_id, ganador_id):
    partido = partido_repository.obtener_por_id(partido_id)

    if ganador_id not in (partido.jugador1_id, partido.jugador2_id):
        raise ResultadoInvalidoError(
            f"El ganador_id ({ganador_id}) debe ser jugador1_id ({partido.jugador1_id}) "
            f"o jugador2_id ({partido.jugador2_id}) de este partido"
        )

    partido_repository.marcar_finalizado(partido_id, ganador_id)

    fase = partido.fase
    torneo_id = partido.torneo_id

    if fase == "cinco_vidas":
        _avanzar_cinco_vidas(torneo_id, partido, ganador_id)
    elif fase == "todos_contra_todos" and _fase_completa(torneo_id, "todos_contra_todos"):
        torneo_repository.marcar_finalizado(torneo_id)
    elif fase == "grupos" and _fase_completa(torneo_id, "grupos"):
        calcular_clasificados(torneo_id)
    elif fase in ("repechaje", "desempate") and _fase_completa(torneo_id, fase):
        resolver_repechaje(torneo_id, partido.grupo_id)
    elif fase == "eliminacion" and _fase_completa(torneo_id, "eliminacion"):
        _generar_siguiente_ronda_eliminacion(torneo_id)
    elif fase == "tercer_puesto" and _fase_completa(torneo_id, "tercer_puesto"):
        _verificar_fin_torneo(torneo_id)

    return partido_repository.obtener_por_id(partido_id).to_dict()


def _fase_completa(torneo_id, fase):
    return partido_repository.contar_pendientes_por_fase(torneo_id, fase) == 0


# =========================================================
# Modo 5 vidas: avance de la cola dinámica
# =========================================================

def _avanzar_cinco_vidas(torneo_id, partido, ganador_id):
    perdedor_id = (
        partido.jugador2_id if ganador_id == partido.jugador1_id
        else partido.jugador1_id
    )

    vidas_restantes = partido_repository.descontar_vida(torneo_id, perdedor_id)

    if vidas_restantes <= 0:
        partido_repository.marcar_eliminado(torneo_id, perdedor_id)
    else:
        nueva_posicion = partido_repository.obtener_ultima_posicion_cola(torneo_id) + 1
        partido_repository.reencolar(torneo_id, perdedor_id, nueva_posicion)

    partido_repository.marcar_en_cancha(torneo_id, ganador_id)

    activos = partido_repository.contar_jugadores_activos(torneo_id)
    if activos <= 1:
        torneo_repository.marcar_finalizado(torneo_id)
        return

    desafiante = partido_repository.obtener_primero_en_cola(torneo_id)

    siguiente_orden = partido_repository.obtener_max_orden(torneo_id) + 1
    partido_repository.crear_uno({
        "torneo_id": torneo_id,
        "jugador1_id": ganador_id,
        "jugador2_id": desafiante["jugador_id"],
        "fase": "cinco_vidas",
        "ronda": None,
        "jornada": None,
        "orden": siguiente_orden,
        "grupo_id": None,
    })


# =========================================================
# Clasificación (fase de grupos -> repechaje/desempate -> eliminación)
# =========================================================

def calcular_clasificados(torneo_id):
    """
    Aplica el reparto proporcional de cupos por grupo (método de mayor resto).
    Si hay empate en el corte, genera un mini-grupo de repechaje.
    Si no hay empate, pasa directo a armar el bracket de eliminación.
    """
    torneo = torneo_repository.obtener_por_id(torneo_id)
    cupos = torneo.cupos_eliminacion
    grupos = [g for g in grupo_repository.obtener_por_torneo(torneo_id) if g.tipo == "grupo"]

    tablas = {g.id: tabla_service.calcular_tabla_grupo(g.id) for g in grupos}
    tamaños = {g.id: len(tablas[g.id]) for g in grupos}
    total_jugadores = sum(tamaños.values())

    cupo_directo, resto = {}, {}
    for g in grupos:
        gid = g.id
        cupo_directo[gid] = (tamaños[gid] * cupos) // total_jugadores
        resto[gid] = (tamaños[gid] * cupos) % total_jugadores

    sobran = cupos - sum(cupo_directo.values())
    orden_restos = sorted(resto, key=lambda gid: resto[gid], reverse=True)

    candidatos_repechaje = []
    slots_repechaje = 0

    if sobran > 0:
        valor_corte = resto[orden_restos[sobran - 1]]
        por_encima = [gid for gid in orden_restos if resto[gid] > valor_corte]
        empatados = [gid for gid in orden_restos if resto[gid] == valor_corte]

        for gid in por_encima:
            cupo_directo[gid] += 1

        slots_restantes = sobran - len(por_encima)
        if slots_restantes == len(empatados):
            # el reparto cierra justo, no hay empate real que resolver
            for gid in empatados:
                cupo_directo[gid] += 1
        else:
            candidatos_repechaje = empatados
            slots_repechaje = slots_restantes

    # Marcar clasificados directos / no clasificados / pendientes de repechaje
    for g in grupos:
        gid = g.id
        tabla = tablas[gid]
        n_directos = cupo_directo[gid]
        for posicion, fila in enumerate(tabla):
            torneo_jugador_id = fila["torneo_jugador_id"]
            if posicion < n_directos:
                torneo_jugador_repository.marcar_clasificado(torneo_jugador_id, True)
            elif gid in candidatos_repechaje and posicion == n_directos:
                torneo_jugador_repository.marcar_clasificado(torneo_jugador_id, None)  # pendiente
            else:
                torneo_jugador_repository.marcar_clasificado(torneo_jugador_id, False)

    if candidatos_repechaje:
        jugadores_repechaje = [
            tablas[gid][cupo_directo[gid]]["jugador_id"] for gid in candidatos_repechaje
        ]
        grupo_id = _crear_grupo_repechaje(torneo_id, jugadores_repechaje, slots_repechaje, tipo="repechaje")
        return {"estado": "repechaje_generado", "candidatos": jugadores_repechaje,
                "slots": slots_repechaje, "grupo_id": grupo_id}
    else:
        generar_fase_eliminacion(torneo_id)
        return {"estado": "eliminacion_generada"}


def resolver_repechaje(torneo_id, grupo_id):
    """Se dispara al terminar un mini-grupo de repechaje o desempate."""
    grupo = grupo_repository.obtener_por_id(grupo_id)
    tabla = tabla_service.calcular_tabla_grupo(grupo_id)
    slots = grupo.slots_a_clasificar

    sin_empate = len(tabla) <= slots or tabla[slots - 1]["puntos"] > tabla[slots]["puntos"]

    if sin_empate:
        for posicion, fila in enumerate(tabla):
            torneo_jugador_repository.marcar_clasificado(
                fila["torneo_jugador_id"], posicion < slots
            )
        generar_fase_eliminacion(torneo_id)
        return {"estado": "eliminacion_generada"}

    # Empate en el corte: no se genera otro grupo solo, se espera decisión del admin
    empatados = [f["jugador_id"] for f in tabla if f["puntos"] == tabla[slots - 1]["puntos"]]
    return {"estado": "empate_sin_resolver", "empatados": empatados, "grupo_id": grupo_id,
            "slots": slots}


def reintentar_desempate(torneo_id, jugadores_empatados_ids, slots):
    """El admin elige 'jugar de nuevo': arma un mini-grupo nuevo (tipo='desempate')."""
    return _crear_grupo_repechaje(torneo_id, jugadores_empatados_ids, slots, tipo="desempate")


def forzar_clasificado(torneo_id, jugador_id, clasificado, observacion=None):
    """El admin decide 'a mano' quién pasa, sin necesidad de jugar más partidos."""
    torneo_jugador_id = torneo_jugador_repository.obtener_id(torneo_id, jugador_id)
    torneo_jugador_repository.marcar_clasificado(
        torneo_jugador_id, clasificado, forzado=True, observacion=observacion
    )
    if not torneo_jugador_repository.hay_pendientes(torneo_id):
        generar_fase_eliminacion(torneo_id)


def _crear_grupo_repechaje(torneo_id, jugadores_ids, slots, tipo):
    grupo_id = grupo_repository.crear(
        torneo_id, nombre=tipo.capitalize(), tipo=tipo, slots_a_clasificar=slots
    )
    torneo_repository.asignar_jugadores_a_grupo(grupo_id, jugadores_ids)

    fixture = _fixture_round_robin(jugadores_ids)
    orden = partido_repository.obtener_max_orden(torneo_id) + 1
    partidos = []
    for jornada, ronda in enumerate(fixture, start=1):
        for j1, j2 in ronda:
            partidos.append({
                "torneo_id": torneo_id, "jugador1_id": j1, "jugador2_id": j2,
                "fase": tipo, "ronda": None, "jornada": jornada, "orden": orden,
                "grupo_id": grupo_id,
            })
            orden += 1
    partido_repository.crear_muchos(partidos)
    return grupo_id


# =========================================================
# Fase de eliminación directa (escalable a cualquier potencia de 2)
# =========================================================

def generar_fase_eliminacion(torneo_id):
    clasificados = torneo_jugador_repository.obtener_clasificados(torneo_id)  # [{jugador_id, grupo_id}]
    orden_bracket = _sembrar_bracket(clasificados)

    orden = partido_repository.obtener_max_orden(torneo_id) + 1
    partidos = []
    for i in range(0, len(orden_bracket), 2):
        partidos.append({
            "torneo_id": torneo_id,
            "jugador1_id": orden_bracket[i],
            "jugador2_id": orden_bracket[i + 1],
            "fase": "eliminacion", "ronda": 1, "jornada": None, "orden": orden,
            "grupo_id": None,
        })
        orden += 1
    partido_repository.crear_muchos(partidos)


def _sembrar_bracket(clasificados):
    """
    Agrupa por grupo de origen e intercala (round-robin entre grupos) para
    minimizar que dos jugadores del mismo grupo se crucen en primera ronda.
    """
    por_grupo = {}
    for c in clasificados:
        por_grupo.setdefault(c["grupo_id"], []).append(c["jugador_id"])
    for lista in por_grupo.values():
        random.shuffle(lista)

    bracket = []
    grupos_restantes = list(por_grupo.values())
    while grupos_restantes:
        for lista in grupos_restantes:
            bracket.append(lista.pop(0))
        grupos_restantes = [l for l in grupos_restantes if l]
    return bracket


def _generar_siguiente_ronda_eliminacion(torneo_id):
    ganadores = partido_repository.obtener_ganadores_ultima_ronda(torneo_id)

    if len(ganadores) == 1:
        # La final ya se jugó. El torneo termina solo si no queda pendiente
        # el partido por el tercer puesto (o si nunca hizo falta generarlo).
        _verificar_fin_torneo(torneo_id)
        return

    ronda_anterior = partido_repository.obtener_ultima_ronda(torneo_id)
    orden = partido_repository.obtener_max_orden(torneo_id) + 1
    partidos = []
    for i in range(0, len(ganadores), 2):
        partidos.append({
            "torneo_id": torneo_id,
            "jugador1_id": ganadores[i], "jugador2_id": ganadores[i + 1],
            "fase": "eliminacion", "ronda": ronda_anterior + 1, "jornada": None, "orden": orden,
            "grupo_id": None,
        })
        orden += 1

    if len(ganadores) == 2:
        # La próxima ronda que se genera es la final -> sumar el partido
        # por el tercer puesto entre los dos perdedores de semifinal.
        perdedores = partido_repository.obtener_perdedores_ultima_ronda(torneo_id)
        partidos.append({
            "torneo_id": torneo_id,
            "jugador1_id": perdedores[0], "jugador2_id": perdedores[1],
            "fase": "tercer_puesto", "ronda": ronda_anterior + 1, "jornada": None, "orden": orden,
            "grupo_id": None,
        })

    partido_repository.crear_muchos(partidos)


def _verificar_fin_torneo(torneo_id):
    """El torneo termina cuando la final está jugada Y (si existía)
    el partido por el tercer puesto también. Si nunca hizo falta generar
    tercer puesto (bracket mínimo de 2 jugadores), esto da 0 igual."""
    if partido_repository.contar_pendientes_por_fase(torneo_id, "tercer_puesto") == 0:
        torneo_repository.marcar_finalizado(torneo_id)