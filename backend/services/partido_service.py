import random

from repositories import partido_repository, torneo_repository, grupo_repository, torneo_jugador_repository
from services import tabla_service


# =========================================================
# Generación de fixture inicial (según modo de torneo)
# =========================================================

def generar_fixture_inicial(torneo_id, modo, jugadores_ids,
                             cupos_eliminacion=None, cantidad_grupos=None,
                             vidas_iniciales=None, orden_jugadores_ids=None):
    if modo == "todos_contra_todos":
        _generar_todos_contra_todos(torneo_id, jugadores_ids)
    elif modo == "grupos_eliminacion":
        _generar_grupos(torneo_id, jugadores_ids, cupos_eliminacion, cantidad_grupos)
    elif modo == "cinco_vidas":
        _generar_cinco_vidas(torneo_id, jugadores_ids, vidas_iniciales, orden_jugadores_ids)


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


def _generar_cinco_vidas(torneo_id, jugadores_ids, vidas_iniciales, orden_jugadores_ids=None):
    """
    Si el admin eligió el orden a mano (drag-and-drop en el frontend), se
    respeta tal cual. Si no, se sortea -- comportamiento de siempre.
    La validación de que orden_jugadores_ids sea realmente una permutación
    de jugadores_ids vive en torneo_service, antes de llegar acá.
    """
    if orden_jugadores_ids is not None:
        orden = list(orden_jugadores_ids)
    else:
        orden = jugadores_ids.copy()
        random.shuffle(orden)

    torneo_repository.inicializar_cola_cinco_vidas(torneo_id, orden, vidas_iniciales)

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


def obtener_estado_actual(torneo_id):
    """
    Pensado para la pantalla de 'partido actual' del frontend: le da un
    panorama completo de qué mostrar, en vez de un simple 404 que no
    distingue 'terminó' de 'está trabado esperando que el admin decida'.
    """
    partido = obtener_partido_actual(torneo_id)
    if partido is not None:
        return {"tipo": "partido", "partido": partido}

    torneo = torneo_repository.obtener_por_id(torneo_id)
    if torneo is not None and torneo.estado == "finalizado":
        return {"tipo": "finalizado"}

    bloqueado = _buscar_grupo_bloqueado(torneo_id)
    if bloqueado is not None:
        return {"tipo": "empate_sin_resolver", **bloqueado}

    return {"tipo": "sin_partidos"}


def _buscar_grupo_bloqueado(torneo_id):
    """Un grupo de repechaje/desempate queda 'bloqueado' cuando terminó
    todos sus partidos pero nadie se marcó clasificado True/False --
    exactamente lo que pasa cuando resolver_repechaje devuelve
    'empate_sin_resolver' y no marca a nadie."""
    grupos = [g for g in grupo_repository.obtener_por_torneo(torneo_id) if g.tipo in ("repechaje", "desempate")]
    for g in grupos:
        completo = partido_repository.contar_pendientes_por_grupo(g.id) == 0
        if completo and torneo_jugador_repository.hay_pendientes_en_grupo(g.id):
            tabla = tabla_service.calcular_tabla_grupo(g.id)
            slots = g.slots_a_clasificar
            empatados = [f["jugador_id"] for f in tabla if f["puntos"] == tabla[slots - 1]["puntos"]]
            return {"grupo_id": g.id, "empatados": empatados, "slots": slots}
    return None


def listar_partidos_pendientes(torneo_id):
    partidos = partido_repository.obtener_pendientes_y_pospuestos(torneo_id)
    return [p.to_dict() for p in partidos]


def listar_partidos(torneo_id):
    """Todos los partidos del torneo (cualquier estado/fase), útil para
    inspeccionar rondas específicas como cuartos, semis, etc."""
    partidos = partido_repository.obtener_por_torneo(torneo_id)
    return [p.to_dict() for p in partidos]


class PartidoInvalidoError(Exception):
    pass


def seleccionar_partido_actual(torneo_id, partido_id):
    """Navegar a otro enfrentamiento. El que estaba en curso queda pospuesto."""
    nuevo_actual = partido_repository.obtener_por_id(partido_id)
    if nuevo_actual is None or nuevo_actual.torneo_id != torneo_id:
        raise PartidoInvalidoError(
            f"El partido {partido_id} no existe o no pertenece al torneo {torneo_id}"
        )

    actual = partido_repository.obtener_en_curso(torneo_id)
    if actual is not None and actual.id != partido_id:
        partido_repository.marcar_pospuesto(actual.id)
    partido_repository.marcar_en_curso(partido_id)
    return partido_repository.obtener_por_id(partido_id).to_dict()


class ResultadoInvalidoError(Exception):
    pass


def marcar_no_realizado(partido_id):
    """
    Partido que no se llegó a jugar (por ejemplo, un jugador que no vino).
    Por ahora solo soportado en todos_contra_todos: en grupos_eliminacion,
    el head-to-head de un empate interno asume que el round-robin del grupo
    está completo, y en cinco_vidas/eliminación no hay un "perdedor" que
    darle a la lógica de avance. Extenderlo a esos modos es trabajo aparte.
    """
    partido = partido_repository.obtener_por_id(partido_id)
    if partido is None:
        raise PartidoInvalidoError(f"No existe el partido {partido_id}")
    if partido.fase != "todos_contra_todos":
        raise PartidoInvalidoError(
            "Por ahora 'no realizado' solo está soportado en el modo todos_contra_todos"
        )
    if partido.estado == "finalizado":
        raise PartidoInvalidoError("Este partido ya tiene un resultado cargado")

    partido_repository.marcar_no_realizado(partido_id)

    if _fase_completa(partido.torneo_id, "todos_contra_todos"):
        torneo_repository.marcar_finalizado(partido.torneo_id)

    return partido_repository.obtener_por_id(partido_id).to_dict()


def cargar_resultado(partido_id, ganador_id, peleador1_id=None, peleador2_id=None, rondas_jugadas=None):
    partido = partido_repository.obtener_por_id(partido_id)
    if partido is None:
        raise PartidoInvalidoError(f"No existe el partido {partido_id}")

    if ganador_id not in (partido.jugador1_id, partido.jugador2_id):
        raise ResultadoInvalidoError(
            f"El ganador_id ({ganador_id}) debe ser jugador1_id ({partido.jugador1_id}) "
            f"o jugador2_id ({partido.jugador2_id}) de este partido"
        )

    if rondas_jugadas is not None:
        if rondas_jugadas not in (2, 3):
            raise ResultadoInvalidoError(
                "rondas_jugadas debe ser 2 (2-0) o 3 (2-1) -- es opcional, se puede omitir"
            )

    partido_repository.marcar_finalizado(partido_id, ganador_id, peleador1_id, peleador2_id, rondas_jugadas)

    fase = partido.fase
    torneo_id = partido.torneo_id

    if fase == "cinco_vidas":
        _avanzar_cinco_vidas(torneo_id, partido, ganador_id)
    elif fase == "todos_contra_todos" and _fase_completa(torneo_id, "todos_contra_todos"):
        torneo_repository.marcar_finalizado(torneo_id)
    elif fase == "grupos" and _fase_completa(torneo_id, "grupos"):
        calcular_clasificados(torneo_id)
    elif fase in ("repechaje", "desempate") and _grupo_completo(partido.grupo_id):
        resolver_repechaje(torneo_id, partido.grupo_id)
    elif fase == "eliminacion" and _fase_completa(torneo_id, "eliminacion"):
        _generar_siguiente_ronda_eliminacion(torneo_id)
    elif fase == "tercer_puesto" and _fase_completa(torneo_id, "tercer_puesto"):
        _verificar_fin_torneo(torneo_id)

    return partido_repository.obtener_por_id(partido_id).to_dict()


def _fase_completa(torneo_id, fase):
    return partido_repository.contar_pendientes_por_fase(torneo_id, fase) == 0


def _grupo_completo(grupo_id):
    """Igual que _fase_completa pero scopeado a una instancia puntual de
    grupo, para no confundir la resolución de desempates/repechajes que
    corren en paralelo en distintos grupos."""
    return partido_repository.contar_pendientes_por_grupo(grupo_id) == 0


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
    Si hay empate en el corte de algún grupo, primero intenta desempatar por
    enfrentamiento directo (sin partidos nuevos); si queda un ciclo real,
    genera un mini-grupo de desempate. El repechaje cruzado entre grupos se
    calcula recién cuando no queda ningún desempate interno pendiente,
    porque hasta entonces no se sabe con certeza quién es "el candidato" de
    cada grupo empatado.
    """
    torneo = torneo_repository.obtener_por_id(torneo_id)
    grupos = [g for g in grupo_repository.obtener_por_torneo(torneo_id) if g.tipo == "grupo"]
    tablas = {g.id: tabla_service.calcular_tabla_grupo(g.id) for g in grupos}
    tamaños = {g.id: len(tablas[g.id]) for g in grupos}

    cupo_directo, candidatos_repechaje, slots_repechaje = _calcular_reparto_cupos(tamaños, torneo.cupos_eliminacion)

    grupos_con_empate_interno = {}  # gid -> (bloque, slots_bloque); ciclo real, necesita mini-grupo

    # Marcar clasificados directos / no clasificados / pendientes
    for g in grupos:
        gid = g.id
        tabla = tablas[gid]
        n_directos = cupo_directo[gid]

        bloque_en_riesgo = tabla_service.detectar_bloque_en_riesgo(tabla, n_directos)
        clasifica_por_id = {}
        if bloque_en_riesgo:
            bloque, slots_bloque = bloque_en_riesgo
            orden_h2h = tabla_service.resolver_por_enfrentamiento_directo(gid, bloque)
            if orden_h2h is not None:
                clasifica_por_id = {
                    f["torneo_jugador_id"]: (i < slots_bloque) for i, f in enumerate(orden_h2h)
                }
            else:
                grupos_con_empate_interno[gid] = (bloque, slots_bloque)

        ids_en_riesgo = (
            {f["torneo_jugador_id"] for f in grupos_con_empate_interno[gid][0]}
            if gid in grupos_con_empate_interno else set()
        )

        for posicion, fila in enumerate(tabla):
            torneo_jugador_id = fila["torneo_jugador_id"]
            if torneo_jugador_id in clasifica_por_id:
                torneo_jugador_repository.marcar_clasificado(
                    torneo_jugador_id, gid, clasifica_por_id[torneo_jugador_id]
                )
            elif torneo_jugador_id in ids_en_riesgo:
                # No puede quedar en NULL acá -- su chance real vive en la
                # fila nueva del mini-grupo de desempate.
                torneo_jugador_repository.marcar_clasificado(torneo_jugador_id, gid, False)
            elif posicion < n_directos:
                torneo_jugador_repository.marcar_clasificado(torneo_jugador_id, gid, True)
            elif gid in candidatos_repechaje and posicion == n_directos:
                torneo_jugador_repository.marcar_clasificado(torneo_jugador_id, gid, False)
            else:
                torneo_jugador_repository.marcar_clasificado(torneo_jugador_id, gid, False)

    for gid, (bloque, slots_bloque) in grupos_con_empate_interno.items():
        jugadores_ids = [f["jugador_id"] for f in bloque]
        _crear_grupo_repechaje(torneo_id, jugadores_ids, slots_bloque, tipo="desempate", grupo_padre_id=gid)

    if grupos_con_empate_interno:
        # El repechaje cruzado (si corresponde) se recalcula recién cuando
        # se resuelvan todos los desempates internos -- ver resolver_repechaje.
        return {"estado": "desempate_interno_generado", "grupos": list(grupos_con_empate_interno.keys())}

    return _resolver_repechaje_cruzado(torneo_id, candidatos_repechaje, slots_repechaje, tablas, cupo_directo)


def _calcular_reparto_cupos(tamaños, cupos):
    """
    Reparto proporcional de cupos directos por grupo (método de mayor
    resto). Depende solo de tamaños de grupo y cupos totales -- no de
    resultados de partidos -- así que es seguro recalcularlo en cualquier
    momento del torneo, siempre da lo mismo.
    """
    total_jugadores = sum(tamaños.values())
    cupo_directo, resto = {}, {}
    for gid, tam in tamaños.items():
        cupo_directo[gid] = (tam * cupos) // total_jugadores
        resto[gid] = (tam * cupos) % total_jugadores

    sobran = cupos - sum(cupo_directo.values())
    orden_restos = sorted(resto, key=lambda gid: resto[gid], reverse=True)

    candidatos_repechaje, slots_repechaje = [], 0
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

    return cupo_directo, candidatos_repechaje, slots_repechaje


def _candidato_de_grupo(gid, tabla_gid, n_directos):
    """
    Devuelve el jugador_id que le corresponde a un grupo como candidato al
    repechaje cruzado. Si ese grupo tuvo un empate interno en el corte, lo
    resuelve (de nuevo, es determinístico porque los partidos del grupo ya
    no cambian) por head-to-head; si fue un ciclo real, usa el resultado ya
    jugado en su mini-grupo de desempate.
    """
    bloque_en_riesgo = tabla_service.detectar_bloque_en_riesgo(tabla_gid, n_directos)
    if not bloque_en_riesgo:
        return tabla_gid[n_directos]["jugador_id"]

    bloque, slots_bloque = bloque_en_riesgo
    orden_h2h = tabla_service.resolver_por_enfrentamiento_directo(gid, bloque)
    if orden_h2h is not None:
        return orden_h2h[slots_bloque]["jugador_id"]

    hijo = grupo_repository.obtener_desempate_interno(gid)
    tabla_hijo = tabla_service.calcular_tabla_grupo(hijo.id)
    return tabla_hijo[hijo.slots_a_clasificar]["jugador_id"]


def _resolver_repechaje_cruzado(torneo_id, candidatos_repechaje, slots_repechaje, tablas, cupo_directo):
    if not candidatos_repechaje:
        generar_fase_eliminacion(torneo_id)
        return {"estado": "eliminacion_generada"}

    jugadores_repechaje = [
        _candidato_de_grupo(gid, tablas[gid], cupo_directo[gid]) for gid in candidatos_repechaje
    ]
    grupo_id = _crear_grupo_repechaje(torneo_id, jugadores_repechaje, slots_repechaje, tipo="repechaje")
    return {"estado": "repechaje_generado", "candidatos": jugadores_repechaje,
            "slots": slots_repechaje, "grupo_id": grupo_id}


def _reintentar_repechaje_cruzado(torneo_id):
    """Recalcula y arma el repechaje cruzado una vez que ya no queda ningún
    desempate interno pendiente en el torneo (ver resolver_repechaje)."""
    torneo = torneo_repository.obtener_por_id(torneo_id)
    grupos = [g for g in grupo_repository.obtener_por_torneo(torneo_id) if g.tipo == "grupo"]
    tablas = {g.id: tabla_service.calcular_tabla_grupo(g.id) for g in grupos}
    tamaños = {g.id: len(tablas[g.id]) for g in grupos}
    cupo_directo, candidatos_repechaje, slots_repechaje = _calcular_reparto_cupos(tamaños, torneo.cupos_eliminacion)
    return _resolver_repechaje_cruzado(torneo_id, candidatos_repechaje, slots_repechaje, tablas, cupo_directo)


def resolver_repechaje(torneo_id, grupo_id):
    """Se dispara al terminar un mini-grupo de repechaje o desempate."""
    grupo = grupo_repository.obtener_por_id(grupo_id)
    tabla = tabla_service.calcular_tabla_grupo(grupo_id)
    slots = grupo.slots_a_clasificar

    sin_empate = len(tabla) <= slots or tabla[slots - 1]["puntos"] > tabla[slots]["puntos"]

    if sin_empate:
        for posicion, fila in enumerate(tabla):
            torneo_jugador_repository.marcar_clasificado(
                fila["torneo_jugador_id"], grupo_id, posicion < slots
            )

        if grupo.grupo_padre_id is not None:
            # Era un desempate interno de grupo. Hasta que no se resuelvan
            # todos los que estén corriendo en paralelo, no sabemos si hace
            # falta armar (o completar) el repechaje cruzado.
            if torneo_jugador_repository.hay_desempates_internos_pendientes(torneo_id):
                return {"estado": "grupo_resuelto_esperando_otros", "grupo_id": grupo_id}
            return _reintentar_repechaje_cruzado(torneo_id)

        if torneo_jugador_repository.hay_pendientes(torneo_id):
            # Todavía hay otro repechaje/desempate corriendo en paralelo en
            # otro grupo -- no generamos el bracket todavía.
            return {"estado": "grupo_resuelto_esperando_otros", "grupo_id": grupo_id}
        generar_fase_eliminacion(torneo_id)
        return {"estado": "eliminacion_generada"}

    # Empate en el corte: no se genera otro grupo solo, se espera decisión del admin
    empatados = [f["jugador_id"] for f in tabla if f["puntos"] == tabla[slots - 1]["puntos"]]
    return {"estado": "empate_sin_resolver", "empatados": empatados, "grupo_id": grupo_id,
            "slots": slots}


class ClasificacionInvalidaError(Exception):
    pass


def reintentar_desempate(torneo_id, jugadores_empatados_ids, slots):
    """El admin elige 'jugar de nuevo': arma un mini-grupo nuevo (tipo='desempate')."""
    if not jugadores_empatados_ids or len(jugadores_empatados_ids) < 2:
        raise ClasificacionInvalidaError("jugadores_empatados_ids necesita al menos 2 jugadores")
    if len(set(jugadores_empatados_ids)) != len(jugadores_empatados_ids):
        raise ClasificacionInvalidaError("jugadores_empatados_ids no puede tener jugadores repetidos")
    if not isinstance(slots, int) or isinstance(slots, bool) or not (1 <= slots < len(jugadores_empatados_ids)):
        raise ClasificacionInvalidaError(
            f"slots debe ser un entero entre 1 y {len(jugadores_empatados_ids) - 1}"
        )
    return _crear_grupo_repechaje(torneo_id, jugadores_empatados_ids, slots, tipo="desempate")


def forzar_clasificado(torneo_id, jugador_id, clasificado, observacion=None):
    """El admin decide 'a mano' quién pasa, sin necesidad de jugar más partidos."""
    if jugador_id is None:
        raise ClasificacionInvalidaError("jugador_id es obligatorio")
    if not isinstance(clasificado, bool):
        raise ClasificacionInvalidaError("clasificado es obligatorio y debe ser true/false")

    torneo_jugador_id = torneo_jugador_repository.obtener_id(torneo_id, jugador_id)
    if torneo_jugador_id is None:
        raise ClasificacionInvalidaError(
            f"El jugador {jugador_id} no participa del torneo {torneo_id}"
        )

    grupo_id = torneo_jugador_repository.obtener_grupo_pendiente(torneo_jugador_id)
    if grupo_id is None:
        raise ClasificacionInvalidaError(
            f"El jugador {jugador_id} no tiene ninguna clasificación pendiente para forzar"
        )

    torneo_jugador_repository.marcar_clasificado(
        torneo_jugador_id, grupo_id, clasificado, forzado=True, observacion=observacion
    )
    if not torneo_jugador_repository.hay_pendientes(torneo_id):
        generar_fase_eliminacion(torneo_id)


def _crear_grupo_repechaje(torneo_id, jugadores_ids, slots, tipo, grupo_padre_id=None):
    grupo_id = grupo_repository.crear(
        torneo_id, nombre=tipo.capitalize(), tipo=tipo, slots_a_clasificar=slots,
        grupo_padre_id=grupo_padre_id,
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

class BracketInvalidoError(Exception):
    pass


def resembrar_bracket_manual(torneo_id, emparejamientos):
    """
    Reemplaza el sembrado automático de la ronda 1 de eliminación por uno
    elegido a mano -- pensado para reconstruir torneos que ya se jugaron
    en la vida real, donde los cruces no salieron del sorteo de
    _sembrar_bracket sino de lo que pasó esa noche. emparejamientos es una
    lista de pares [jugador1_id, jugador2_id]. Solo se puede usar si la
    ronda 1 todavía no tiene ningún resultado cargado.
    """
    partidos_ronda1 = partido_repository.obtener_por_fase_y_ronda(torneo_id, "eliminacion", 1)
    if not partidos_ronda1:
        raise BracketInvalidoError("Todavía no se generó el bracket de eliminación para este torneo")
    if any(p.estado != "pendiente" for p in partidos_ronda1):
        raise BracketInvalidoError(
            "Ya se jugó al menos un partido de la ronda 1 -- no se puede resembrar"
        )

    clasificados_ids = {jid for p in partidos_ronda1 for jid in (p.jugador1_id, p.jugador2_id)}
    ids_en_emparejamientos = [jid for par in emparejamientos for jid in par]

    if len(emparejamientos) != len(partidos_ronda1):
        raise BracketInvalidoError(
            f"Se esperaban {len(partidos_ronda1)} enfrentamientos, llegaron {len(emparejamientos)}"
        )
    if any(len(par) != 2 for par in emparejamientos):
        raise BracketInvalidoError("Cada enfrentamiento debe tener exactamente 2 jugadores")
    if len(set(ids_en_emparejamientos)) != len(ids_en_emparejamientos):
        raise BracketInvalidoError("Un jugador no puede aparecer en más de un enfrentamiento")
    if set(ids_en_emparejamientos) != clasificados_ids:
        raise BracketInvalidoError(
            "Los emparejamientos deben incluir exactamente a los jugadores clasificados, "
            "sin repetidos ni faltantes"
        )

    orden_base = min(p.orden for p in partidos_ronda1)
    for p in partidos_ronda1:
        partido_repository.eliminar(p.id)

    nuevos = [
        {
            "torneo_id": torneo_id, "jugador1_id": j1, "jugador2_id": j2,
            "fase": "eliminacion", "ronda": 1, "jornada": None, "orden": orden_base + i,
            "grupo_id": None,
        }
        for i, (j1, j2) in enumerate(emparejamientos)
    ]
    partido_repository.crear_muchos(nuevos)


def obtener_bracket_ronda1(torneo_id):
    return [p.to_dict() for p in partido_repository.obtener_por_fase_y_ronda(torneo_id, "eliminacion", 1)]


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

    if len(ganadores) == 2:
        # La próxima ronda que se genera es la final. El partido por el
        # tercer puesto se arma primero (orden más bajo) para que se juegue
        # antes que la final, no después.
        perdedores = partido_repository.obtener_perdedores_ultima_ronda(torneo_id)
        partidos.append({
            "torneo_id": torneo_id,
            "jugador1_id": perdedores[0], "jugador2_id": perdedores[1],
            "fase": "tercer_puesto", "ronda": ronda_anterior + 1, "jornada": None, "orden": orden,
            "grupo_id": None,
        })
        orden += 1

    for i in range(0, len(ganadores), 2):
        partidos.append({
            "torneo_id": torneo_id,
            "jugador1_id": ganadores[i], "jugador2_id": ganadores[i + 1],
            "fase": "eliminacion", "ronda": ronda_anterior + 1, "jornada": None, "orden": orden,
            "grupo_id": None,
        })
        orden += 1

    partido_repository.crear_muchos(partidos)


def _verificar_fin_torneo(torneo_id):
    """El torneo termina cuando la final está jugada Y (si existía)
    el partido por el tercer puesto también. Si nunca hizo falta generar
    tercer puesto (bracket mínimo de 2 jugadores), esto da 0 igual."""
    if partido_repository.contar_pendientes_por_fase(torneo_id, "tercer_puesto") == 0:
        torneo_repository.marcar_finalizado(torneo_id)