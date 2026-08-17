from repositories import partido_repository, torneo_jugador_repository, grupo_repository, jugador_repository, torneo_repository


def calcular_tabla_rey_de_la_cancha(torneo_id, vidas_prefetch=None, partidos_prefetch=None, nombres_prefetch=None):
    """
    Tabla de posiciones de un torneo rey_de_la_cancha: puesto (80% puntos de
    racha + 20% posición final -- ver el diseño largo que se charló para
    este criterio), puntos de racha, y momento de eliminación de cada
    jugador. El campeón siempre es puesto 1.

    Los tres *_prefetch son opcionales -- si no se pasan, esta función
    consulta la base por su cuenta (uso normal, para ver un torneo
    puntual). Cuando SÍ se pasan (lo hace tabla_general_service al
    recorrer todos los torneos para el ranking general), se usan esos
    datos ya en memoria en vez de volver a pedirlos -- evita repetir 3
    consultas por cada torneo rey_de_la_cancha del historial.
    """
    PESO_RACHA = 0.8
    PESO_POSICION = 0.2

    filas = vidas_prefetch if vidas_prefetch is not None else torneo_jugador_repository.obtener_vidas_de_torneo(torneo_id)
    if partidos_prefetch is not None:
        partidos = sorted(
            [p for p in partidos_prefetch if p.fase == "rey_de_la_cancha"],
            key=lambda p: p.orden,
        )
    else:
        partidos = sorted(
            partido_repository.obtener_finalizados_por_torneo(torneo_id, "rey_de_la_cancha", []),
            key=lambda p: p.orden,
        )
    nombres = nombres_prefetch if nombres_prefetch is not None else {j.id: j.nombre for j in jugador_repository.obtener_todos()}

    racha_actual = {}
    puntos_racha = {}

    def _cerrar_racha(jugador_id):
        largo = racha_actual.get(jugador_id, 0)
        if largo > 0:
            puntos_racha[jugador_id] = puntos_racha.get(jugador_id, 0) + largo ** 2
        racha_actual[jugador_id] = 0

    for p in partidos:
        perdedor_id = p.jugador2_id if p.ganador_id == p.jugador1_id else p.jugador1_id
        racha_actual[p.ganador_id] = racha_actual.get(p.ganador_id, 0) + 1
        _cerrar_racha(perdedor_id)

    campeon_id = next((f["jugador_id"] for f in filas if not f["eliminado"]), None)
    if campeon_id is not None:
        _cerrar_racha(campeon_id)  # la racha activa del campeón también cuenta

    eliminados = [f for f in filas if f["eliminado"]]
    puestos = {campeon_id: 1} if campeon_id is not None else {}

    if eliminados:
        r_valores = [puntos_racha.get(f["jugador_id"], 0) for f in eliminados]
        t_valores = [f["orden_eliminacion"] for f in eliminados]
        r_min, r_max = min(r_valores), max(r_valores)
        t_min, t_max = min(t_valores), max(t_valores)

        def _normalizar(valor, minimo, maximo):
            return (valor - minimo) / (maximo - minimo) if maximo > minimo else 0.5

        def _score(f):
            r = _normalizar(puntos_racha.get(f["jugador_id"], 0), r_min, r_max)
            t = _normalizar(f["orden_eliminacion"], t_min, t_max)
            return PESO_RACHA * r + PESO_POSICION * t

        eliminados_ordenados = sorted(eliminados, key=lambda f: -_score(f))
        puesto_actual = 1  # arranca en 1 porque el campeón ya ocupó el puesto 1
        score_anterior = None
        for f in eliminados_ordenados:
            score = round(_score(f), 9)
            if score != score_anterior:
                puesto_actual += 1
                score_anterior = score
            puestos[f["jugador_id"]] = puesto_actual

    tabla = [
        {
            "jugador_id": f["jugador_id"],
            "nombre": nombres.get(f["jugador_id"]),
            "puesto": puestos.get(f["jugador_id"]),
            "puntos_racha": puntos_racha.get(f["jugador_id"], 0),
            "orden_eliminacion": f["orden_eliminacion"],
            "eliminado": f["eliminado"],
        }
        for f in filas
    ]
    # Solo el emoji, que es cosmético. El ORDEN de este modo lo define el
    # puesto que sale de la fórmula (80% racha² + 20% posición final) y no
    # se toca: acá el win rate no ordena ni desempata, porque el mérito se
    # mide por las rachas, no por la proporción de partidos ganados.
    from services import tabla_general_service
    for f in tabla:
        f["emoji"] = tabla_general_service.emoji_por_puesto(f["puesto"]) if f["puesto"] else ""

    tabla.sort(key=lambda f: f["puesto"])
    return tabla


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

    Si el torneo tiene los grupos en formato rey de la cancha, el orden NO
    sale de sumar victorias sino de la misma fórmula que usa ese modo
    (racha² + qué tan lejos llegaste). De ahí salen también los que
    clasifican a la eliminación.
    """
    partidos_excluidos_ids = partidos_excluidos_ids or []

    grupo = grupo_repository.obtener_por_id(grupo_id)
    if grupo is not None:
        torneo = torneo_repository.obtener_por_id(grupo.torneo_id)
        if torneo is not None and torneo.formato_grupos == "rey_de_la_cancha":
            return _tabla_grupo_rey_de_la_cancha(grupo_id, grupo.torneo_id)
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

    for f in tabla.values():
        f["win_rate"] = round(f["pg"] / f["pj"], 3) if f["pj"] else 0

    # Sin emoji a propósito: acá el orden es DENTRO del grupo, no del torneo.
    # Un 🥇 en la tabla de un grupo daría a entender que ganó el torneo.
    return sorted(tabla.values(), key=lambda f: (-f["puntos"], -f["win_rate"]))



def _tabla_grupo_rey_de_la_cancha(grupo_id, torneo_id):
    """
    Tabla de un grupo que se jugó a rey de la cancha.

    Reusa calcular_tabla_rey_de_la_cancha pasándole SOLO los datos de este
    grupo: las vidas de sus jugadores y los partidos de ese grupo. Así la
    fórmula (racha² + posición final) es exactamente la misma que en el
    modo suelto -- si se recalculara acá con otro criterio, un mismo
    resultado podría ordenarse distinto según dónde se mire.

    Se adapta el nombre de los campos a los que espera el resto del código
    de grupos (pj/pg/pp/puntos), para que las pantallas y el cálculo de
    clasificados no tengan que saber de qué formato viene la tabla.
    """
    vidas = torneo_jugador_repository.obtener_vidas_de_grupo(grupo_id)
    partidos = [p for p in partido_repository.obtener_por_torneo(torneo_id)
                if p.grupo_id == grupo_id and p.estado == "finalizado"]
    nombres = {j.id: j.nombre for j in jugador_repository.obtener_todos()}
    # El código de clasificación y desempates identifica a cada jugador por
    # su torneo_jugador_id, no por jugador_id. La tabla de rey de la cancha
    # no lo trae (no lo necesita para su cálculo), así que se busca acá para
    # que las filas queden con la misma forma que las de todos contra todos.
    jugadores_grupo = torneo_jugador_repository.obtener_jugadores_de_grupo(grupo_id)
    tj_por_jugador = {j["jugador_id"]: j["torneo_jugador_id"] for j in jugadores_grupo}

    # calcular_tabla_rey_de_la_cancha filtra por fase == "rey_de_la_cancha", pero acá
    # los partidos son de fase "grupos": se les cambia la etiqueta solo para
    # este cálculo, sin tocar nada en la base.
    class _PartidoComoCincoVidas:
        def __init__(self, p):
            self._p = p
            self.fase = "rey_de_la_cancha"
        def __getattr__(self, nombre):
            return getattr(self._p, nombre)

    tabla = calcular_tabla_rey_de_la_cancha(
        torneo_id,
        vidas_prefetch=vidas,
        partidos_prefetch=[_PartidoComoCincoVidas(p) for p in partidos],
        nombres_prefetch=nombres,
    )

    # Estadísticas de partidos, que la tabla de cinco vidas no trae pero el
    # resto del código de grupos sí espera.
    stats = {v["jugador_id"]: {"pj": 0, "pg": 0, "pp": 0} for v in vidas}
    for p in partidos:
        perdedor = p.jugador2_id if p.ganador_id == p.jugador1_id else p.jugador1_id
        if p.ganador_id in stats:
            stats[p.ganador_id]["pj"] += 1
            stats[p.ganador_id]["pg"] += 1
        if perdedor in stats:
            stats[perdedor]["pj"] += 1
            stats[perdedor]["pp"] += 1

    for fila in tabla:
        fila["torneo_jugador_id"] = tj_por_jugador.get(fila["jugador_id"])
        s = stats.get(fila["jugador_id"], {"pj": 0, "pg": 0, "pp": 0})
        fila.update(s)
        fila["win_rate"] = round(s["pg"] / s["pj"], 3) if s["pj"] else 0
        # "puntos" existe para que el código de clasificados/desempates, que
        # es común a los dos formatos, siga funcionando sin cambios.
        #
        # OJO con qué se pone acá: usar los puntos de RACHA parecía lo
        # natural, pero deja en 0 a todos los que nunca encadenaron dos
        # victorias -- y ese cero los hace figurar como "empatados", lo que
        # dispara desempates que no corresponden. El puesto ya los distingue
        # bien (2°, 3°, 4°), así que se deriva de ahí: más alto el puesto,
        # más puntos. Así el corte de clasificación respeta exactamente el
        # orden de la tabla.
        fila["puntos"] = len(tabla) - fila["puesto"] + 1

    return tabla


def calcular_tabla_todos_contra_todos(torneo_id, partidos_excluidos_ids=None, jugadores_prefetch=None, partidos_prefetch=None):
    """Misma lógica que calcular_tabla_grupo, pero sin filtrar por grupo.

    jugadores_prefetch/partidos_prefetch opcionales -- ver el mismo
    criterio explicado en calcular_tabla_rey_de_la_cancha. Si se pasa
    partidos_prefetch, tiene que venir SIN excluidos aplicados (el
    filtro de excluidos, cuando hace falta, solo se soporta consultando
    fresco -- que es lo que ya hacen todos los llamadores que usan
    excluidos hoy)."""
    partidos_excluidos_ids = partidos_excluidos_ids or []
    jugadores = jugadores_prefetch if jugadores_prefetch is not None else torneo_jugador_repository.obtener_jugadores_de_torneo(torneo_id)
    if partidos_prefetch is not None:
        partidos = [p for p in partidos_prefetch if p.fase == "todos_contra_todos"]
    else:
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

    from services import tabla_general_service

    filas = sorted(tabla.values(), key=lambda f: f["puntos"], reverse=True)

    # Puesto denso, el mismo criterio que en el resto del proyecto: los que
    # empatan en puntos comparten puesto, y el siguiente grupo pasa al
    # número que sigue sin saltear (1,1,1,2 y no 1,1,1,4).
    puesto_actual = 0
    puntos_anteriores = None
    for fila in filas:
        if fila["puntos"] != puntos_anteriores:
            puesto_actual += 1
            puntos_anteriores = fila["puntos"]
        fila["puesto"] = puesto_actual
        fila["win_rate"] = round(fila["pg"] / fila["pj"], 3) if fila["pj"] else 0
        fila["emoji"] = tabla_general_service.emoji_por_puesto(puesto_actual)

    # Dentro de un mismo puesto (mismos puntos), primero el de mejor win
    # rate. No cambia las posiciones -- solo ordena a los empatados.
    filas.sort(key=lambda f: (f["puesto"], -f["win_rate"]))
    return filas


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

def calcular_tabla_grupos_eliminacion(torneo_id):
    """
    Tabla general de un torneo de grupos + eliminación: la posición final
    de TODOS los participantes, no solo del podio.

    El puesto no sale de sumar puntos como en los otros modos, sino de
    hasta dónde llegó cada uno en la eliminación (campeón, finalista,
    tercero, cuarto, cuartos, y el resto). Esa lógica ya existe y es la
    que usa la tabla histórica para repartir puntos, así que se reutiliza
    tal cual -- si se recalculara acá con otro criterio, la tabla del
    torneo y el ranking general podrían llegar a contradecirse.

    A cada jugador se le suman además sus partidos del torneo (todas las
    fases), para que la tabla diga algo más que el puesto.
    """
    from services import tabla_general_service

    torneo = torneo_repository.obtener_por_id(torneo_id)
    if torneo is None:
        return []

    puestos = tabla_general_service.calcular_puestos(torneo)
    jugadores = torneo_jugador_repository.obtener_jugadores_de_torneo(torneo_id)
    partidos = partido_repository.obtener_por_torneo(torneo_id)

    filas = {
        j["jugador_id"]: {
            "jugador_id": j["jugador_id"],
            "nombre": j["nombre"],
            "puesto": puestos.get(j["jugador_id"]),
            "pj": 0, "pg": 0, "pp": 0,
        }
        for j in jugadores
    }

    for p in partidos:
        if p.estado != "finalizado" or p.ganador_id is None:
            continue
        perdedor_id = p.jugador2_id if p.ganador_id == p.jugador1_id else p.jugador1_id
        if p.ganador_id in filas:
            filas[p.ganador_id]["pj"] += 1
            filas[p.ganador_id]["pg"] += 1
        if perdedor_id in filas:
            filas[perdedor_id]["pj"] += 1
            filas[perdedor_id]["pp"] += 1

    for f in filas.values():
        f["win_rate"] = round(f["pg"] / f["pj"], 3) if f["pj"] else 0
        f["emoji"] = tabla_general_service.emoji_por_puesto(f["puesto"]) if f["puesto"] else ""

    # Por puesto, y entre los que comparten puesto (los eliminados en la
    # misma instancia), primero el de mejor win rate.
    return sorted(filas.values(), key=lambda f: (f["puesto"] or 99, -f["win_rate"], f["nombre"]))
