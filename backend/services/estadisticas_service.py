from repositories import (
    torneo_repository, partido_repository, jugador_repository,
    peleador_repository, torneo_jugador_repository,
)
from services import tabla_general_service, rating_service, estadisticas_config_service, cache_resultados


class JugadorNoEncontradoError(Exception):
    pass


# Un peleador necesita al menos esta cantidad de partidos jugados para
# entrar en el ranking de "mejor win rate" -- si no, un jugador con 1
# partido y 1 victoria con un peleador random le gana a todos con 100%.
PELEADOR_MIN_PARTIDOS_PARA_WIN_RATE = 3


def _todos_los_maximos(lista, key):
    """Devuelve TODOS los que empatan en el valor máximo, no solo uno --
    max()/lista[0] de Python solo devuelven un elemento aunque haya
    varios empatados, y para estas estadísticas eso esconde información
    real (ej: si le ganaste 3 veces a 3 rivales distintos, los 3 son
    'el rival más vencido', no solo el primero que aparezca)."""
    if not lista:
        return []
    m = max(key(f) for f in lista)
    return [f for f in lista if key(f) == m]


def _todos_los_minimos(lista, key):
    if not lista:
        return []
    m = min(key(f) for f in lista)
    return [f for f in lista if key(f) == m]


def obtener_estadisticas_jugador(jugador_id: int) -> dict:
    jugador = jugador_repository.obtener_por_id(jugador_id)
    if jugador is None:
        raise JugadorNoEncontradoError(f"No existe el jugador {jugador_id}")

    partidos = partido_repository.obtener_finalizados_por_jugador(jugador_id)
    torneos_finalizados = torneo_repository.obtener_finalizados_de_jugador(jugador_id)
    torneos_todos = torneo_repository.obtener_todos_de_jugador(jugador_id)

    # Todo esto lo necesitan VARIAS de las funciones de abajo. Si cada una
    # lo pidiera por su cuenta (que es lo que pasaba antes), un solo perfil
    # terminaba consultando la lista de jugadores 3 veces, la de peleadores
    # 2, y recalculando Bradley-Terry sobre TODO el historial 2 veces. Se
    # trae una sola vez acá y se reparte.
    nombres = {j.id: j.nombre for j in jugador_repository.obtener_todos()}
    nombres_peleador = {pl.id: pl.nombre for pl in peleador_repository.obtener_todos()}
    probabilidades = _probabilidades_con_nombres(nombres)

    resultado = {
        "jugador_id": jugador_id,
        "nombre": jugador.nombre,
        "resumen_general": _resumen_general(jugador_id, partidos),
        "ultimos_resultados": _ultimos_resultados(jugador_id, partidos),
        "rivales": _stats_rivales(jugador_id, partidos, nombres),
        "peleadores": _stats_peleadores(jugador_id, partidos, nombres_peleador),
        "peleadores_rivales": _stats_peleadores_rivales(jugador_id, partidos, nombres_peleador),
        "rachas": _stats_rachas(jugador_id, partidos),
        "rounds": _stats_rounds(jugador_id, partidos),
        "torneos": _stats_torneos(jugador_id, torneos_finalizados, torneos_todos),
        "cinco_vidas": _stats_cinco_vidas(jugador_id, torneos_finalizados, nombres),
        "veces_en_repechaje_o_desempate": torneo_jugador_repository.contar_repechajes_y_desempates(jugador_id),
        "mejores_victorias": _mejores_victorias(jugador_id, probabilidades=probabilidades),
        "peores_caidas": _peores_caidas(jugador_id, probabilidades=probabilidades),
    }

    # Los campos de nivel superior primero...
    resultado = estadisticas_config_service.filtrar_visibles(
        resultado, "jugador",
        campos_lista=("ultimos_resultados", "mejores_victorias", "peores_caidas"),
    )
    # ...y después cada sub-diccionario anidado, con su propio prefijo --
    # 'mas_frecuente' existe en 'peleadores' Y en 'peleadores_rivales', así
    # que no alcanza con un solo prefijo 'jugador' para todo.
    if resultado["rivales"]:
        resultado["rivales"] = estadisticas_config_service.filtrar_visibles(
            resultado["rivales"], "jugador.rivales",
            campos_lista=("rival_mas_vencido", "rival_mas_frecuente", "matchup_parejo", "nemesis"),
        )
    if resultado["peleadores"]:
        resultado["peleadores"] = estadisticas_config_service.filtrar_visibles(
            resultado["peleadores"], "jugador.peleadores",
            campos_lista=("mas_frecuente", "mejor_win_rate", "peor_win_rate"),
        )
    if resultado["peleadores_rivales"]:
        resultado["peleadores_rivales"] = estadisticas_config_service.filtrar_visibles(
            resultado["peleadores_rivales"], "jugador.peleadores_rivales",
            campos_lista=("mas_frecuente", "que_te_gana_mas", "que_le_ganas_mas"),
        )
    if resultado["torneos"]:
        resultado["torneos"] = estadisticas_config_service.filtrar_visibles(
            resultado["torneos"], "jugador.torneos",
            campos_lista=("mejor_puesto_historico",),
        )
    if resultado["cinco_vidas"]:
        resultado["cinco_vidas"] = estadisticas_config_service.filtrar_visibles(
            resultado["cinco_vidas"], "jugador.cinco_vidas",
            campos_lista=("quien_te_elimino_mas", "a_quien_eliminaste_mas"),
        )

    return resultado


def _mejores_victorias(jugador_id, top_n=5, probabilidades=None):
    """Tus victorias más sorpresivas -- ganaste con menor probabilidad
    según el rating (Bradley-Terry) del rival en ese momento del
    historial completo. Top 5 con empates (no se decide arbitrariamente
    cuál va antes si dan exactamente igual de sorpresivo)."""
    probabilidades = probabilidades if probabilidades is not None else _probabilidades_con_nombres()
    propias = [f for f in probabilidades if f["ganador_id"] == jugador_id]
    return _top_n_con_empates(propias, key=lambda f: -f["probabilidad_ganador"], n=top_n)


def _peores_caidas(jugador_id, top_n=5, probabilidades=None):
    """Tus derrotas más sorpresivas -- perdiste siendo favorito según el
    rating (probabilidad baja de que gane el rival, y aun así ganó)."""
    probabilidades = probabilidades if probabilidades is not None else _probabilidades_con_nombres()
    propias = [f for f in probabilidades if f["perdedor_id"] == jugador_id]
    return _top_n_con_empates(propias, key=lambda f: -f["probabilidad_ganador"], n=top_n)


def _probabilidades_con_nombres(nombres=None):
    """calcular_probabilidades_resultados() solo trae ids -- acá se le
    pegan los nombres, para no tener que hacerlo en cada función que la
    usa (y para no repetir el bug de mostrar el % sin decir contra
    quién)."""
    probabilidades = rating_service.calcular_probabilidades_resultados()
    nombres = nombres if nombres is not None else {j.id: j.nombre for j in jugador_repository.obtener_todos()}
    for f in probabilidades:
        f["ganador_nombre"] = nombres.get(f["ganador_id"])
        f["perdedor_nombre"] = nombres.get(f["perdedor_id"])
    return probabilidades


def _top_n_con_empates(lista, key, n=5):
    """Mismo criterio que en estadisticas_generales_service: primeros N
    valores DISTINTOS de key, con todos los empates incluidos."""
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


def _ultimos_resultados(jugador_id, partidos, cantidad=5):
    """Los ultimos N resultados en orden cronologico (mas viejo primero,
    igual que 'partidos'), como 'G'/'P' -- forma reciente de un vistazo."""
    ultimos = partidos[-cantidad:]
    return ["G" if p.ganador_id == jugador_id else "P" for p in ultimos]


def _resumen_general(jugador_id, partidos):
    jugados = len(partidos)
    ganados = sum(1 for p in partidos if p.ganador_id == jugador_id)
    return {
        "partidos_jugados": jugados,
        "partidos_ganados": ganados,
        "partidos_perdidos": jugados - ganados,
        "win_rate": round(ganados / jugados, 3) if jugados > 0 else 0,
    }


# Piso mínimo de partidos para que "matchup parejo" o "nemesis" no salgan
# de una muestra ridícula (ej: 1-0 no es un "matchup parejo" real).
RIVAL_MIN_PARTIDOS_PARA_MATCHUP = 3


def _stats_rivales(jugador_id, partidos, nombres=None):
    """'A quién le ganó más' y 'rival más frecuente' son preguntas
    distintas (frecuencia vs. victorias), así que se calculan por
    separado aunque salgan de la misma tabla."""
    contra_rival = {}
    for p in partidos:
        rival_id = p.jugador2_id if p.jugador1_id == jugador_id else p.jugador1_id
        entrada = contra_rival.setdefault(rival_id, {
            "jugador_id": rival_id, "partidos_jugados": 0,
            "partidos_ganados": 0, "partidos_perdidos": 0,
        })
        entrada["partidos_jugados"] += 1
        if p.ganador_id == jugador_id:
            entrada["partidos_ganados"] += 1
        else:
            entrada["partidos_perdidos"] += 1

    nombres = nombres if nombres is not None else {j.id: j.nombre for j in jugador_repository.obtener_todos()}
    lista = list(contra_rival.values())
    for entrada in lista:
        entrada["nombre"] = nombres.get(entrada["jugador_id"])
        entrada["win_rate"] = round(entrada["partidos_ganados"] / entrada["partidos_jugados"], 3)
    lista.sort(key=lambda f: -f["partidos_jugados"])

    candidatos_matchup = [f for f in lista if f["partidos_jugados"] >= RIVAL_MIN_PARTIDOS_PARA_MATCHUP]
    matchup_parejo = _todos_los_minimos(
        candidatos_matchup, key=lambda f: abs(f["partidos_ganados"] - f["partidos_perdidos"])
    )
    nemesis = _todos_los_minimos(candidatos_matchup, key=lambda f: f["win_rate"])

    return {
        "rival_mas_vencido": _todos_los_maximos(lista, key=lambda f: f["partidos_ganados"]),
        "rival_mas_frecuente": _todos_los_maximos(lista, key=lambda f: f["partidos_jugados"]),
        "matchup_parejo": matchup_parejo,
        "nemesis": nemesis,
        "min_partidos_para_matchup": RIVAL_MIN_PARTIDOS_PARA_MATCHUP,
        "todos": lista,
    }


def _stats_peleadores(jugador_id, partidos, nombres_peleador=None):
    """Excluye cinco_vidas a propósito -- no se trackea peleador en ese modo."""
    contra_peleador = {}
    for p in partidos:
        if p.fase == "cinco_vidas":
            continue
        peleador_id = p.jugador1_peleador_id if p.jugador1_id == jugador_id else p.jugador2_peleador_id
        if peleador_id is None:
            continue
        entrada = contra_peleador.setdefault(peleador_id, {
            "peleador_id": peleador_id, "partidos_jugados": 0, "partidos_ganados": 0,
        })
        entrada["partidos_jugados"] += 1
        if p.ganador_id == jugador_id:
            entrada["partidos_ganados"] += 1

    nombres_peleador = nombres_peleador if nombres_peleador is not None else {pl.id: pl.nombre for pl in peleador_repository.obtener_todos()}
    lista = []
    for entrada in contra_peleador.values():
        entrada["nombre"] = nombres_peleador.get(entrada["peleador_id"])
        entrada["win_rate"] = round(entrada["partidos_ganados"] / entrada["partidos_jugados"], 3)
        lista.append(entrada)
    lista.sort(key=lambda f: -f["partidos_jugados"])

    candidatos_win_rate = [f for f in lista if f["partidos_jugados"] >= PELEADOR_MIN_PARTIDOS_PARA_WIN_RATE]

    return {
        "mas_frecuente": _todos_los_maximos(lista, key=lambda f: f["partidos_jugados"]),
        "mejor_win_rate": _todos_los_maximos(candidatos_win_rate, key=lambda f: f["win_rate"]),
        "peor_win_rate": _todos_los_minimos(candidatos_win_rate, key=lambda f: f["win_rate"]),
        "min_partidos_para_win_rate": PELEADOR_MIN_PARTIDOS_PARA_WIN_RATE,
        "todos": lista,
    }


def _stats_peleadores_rivales(jugador_id, partidos, nombres_peleador=None):
    """El espejo de _stats_peleadores: acá no importa qué peleador usás
    vos, sino qué peleador usa el RIVAL en tu contra. 'Que te gana más' y
    'que le ganás más' son conteos (no win rate) para que sea consistente
    con cómo ya se responde 'a quién le ganó más' en _stats_rivales."""
    contra_peleador_rival = {}
    for p in partidos:
        if p.fase == "cinco_vidas":
            continue
        peleador_rival_id = p.jugador2_peleador_id if p.jugador1_id == jugador_id else p.jugador1_peleador_id
        if peleador_rival_id is None:
            continue
        entrada = contra_peleador_rival.setdefault(peleador_rival_id, {
            "peleador_id": peleador_rival_id, "partidos_jugados": 0,
            "partidos_ganados": 0, "partidos_perdidos": 0,
        })
        entrada["partidos_jugados"] += 1
        if p.ganador_id == jugador_id:
            entrada["partidos_ganados"] += 1
        else:
            entrada["partidos_perdidos"] += 1

    nombres_peleador = nombres_peleador if nombres_peleador is not None else {pl.id: pl.nombre for pl in peleador_repository.obtener_todos()}
    lista = list(contra_peleador_rival.values())
    for entrada in lista:
        entrada["nombre"] = nombres_peleador.get(entrada["peleador_id"])
    lista.sort(key=lambda f: -f["partidos_jugados"])

    return {
        "mas_frecuente": _todos_los_maximos(lista, key=lambda f: f["partidos_jugados"]),
        "que_te_gana_mas": _todos_los_maximos(lista, key=lambda f: f["partidos_perdidos"]),
        "que_le_ganas_mas": _todos_los_maximos(lista, key=lambda f: f["partidos_ganados"]),
        "todos": lista,
    }


def _stats_rachas(jugador_id, partidos):
    """partidos ya viene ordenado cronológicamente (ORDER BY fecha_jugado
    ASC en el repository). 'Racha actual' cuenta desde el partido más
    reciente hacia atrás, del mismo signo (ganando o perdiendo)."""
    if not partidos:
        return {"mejor_racha_ganadora_historica": 0, "racha_actual": 0, "racha_actual_tipo": None}

    resultados = [p.ganador_id == jugador_id for p in partidos]

    mejor_racha_ganadora = 0
    racha_en_curso = 0
    for gano in resultados:
        racha_en_curso = racha_en_curso + 1 if gano else 0
        mejor_racha_ganadora = max(mejor_racha_ganadora, racha_en_curso)

    ultimo_resultado = resultados[-1]
    racha_actual = 0
    for gano in reversed(resultados):
        if gano != ultimo_resultado:
            break
        racha_actual += 1

    return {
        "mejor_racha_ganadora_historica": mejor_racha_ganadora,
        "racha_actual": racha_actual,
        "racha_actual_tipo": "ganando" if ultimo_resultado else "perdiendo",
    }


def _stats_torneos(jugador_id, torneos_finalizados, torneos_todos):
    por_modo = {}
    for t in torneos_todos:
        por_modo[t.modo] = por_modo.get(t.modo, 0) + 1

    # El puesto del jugador en cada torneo YA está calculado dentro de la
    # tabla general (viene en sus insignias), que además está cacheada y
    # precalentada al arrancar. Antes esto recalculaba el puesto de cada
    # torneo desde cero, con 2 o 3 consultas por torneo -- o sea que un
    # solo perfil disparaba decenas de consultas para llegar a un número
    # que ya estaba a mano.
    tabla = cache_resultados.obtener(
        "tabla-general:[]", tabla_general_service.calcular_tabla_general
    )
    fila_propia = next((f for f in tabla if f["jugador_id"] == jugador_id), None)
    insignias = fila_propia["insignias"] if fila_propia else []

    mejor_puesto_valor = None
    mejor_puesto_torneos = []
    veces_campeon = 0
    suma_puestos = 0
    cantidad_puestos = 0
    for ins in insignias:
        puesto = ins["puesto"]
        suma_puestos += puesto
        cantidad_puestos += 1
        if puesto == 1:
            veces_campeon += 1
        entrada = {"torneo_id": ins["torneo_id"], "nombre": ins["torneo_nombre"], "puesto": puesto}
        if mejor_puesto_valor is None or puesto < mejor_puesto_valor:
            mejor_puesto_valor = puesto
            mejor_puesto_torneos = [entrada]
        elif puesto == mejor_puesto_valor:
            mejor_puesto_torneos.append(entrada)

    return {
        "torneos_jugados_por_modo": por_modo,
        "torneos_jugados_total": len(torneos_todos),
        "veces_campeon": veces_campeon,
        "mejor_puesto_historico": mejor_puesto_torneos,
        "promedio_puesto": round(suma_puestos / cantidad_puestos, 2) if cantidad_puestos else None,
    }


def _stats_rounds(jugador_id, partidos):
    """
    2 rounds jugados = 2-0 (barrida). 3 rounds jugados = 2-1 (cerrado).
    rondas_jugadas es opcional por partido -- solo cuenta los que sí lo
    tienen cargado, el resto se ignora sin romper el promedio.
    """
    rounds_ganados = 0
    rounds_perdidos = 0
    barridas_hechas = 0
    barridas_recibidas = 0
    cerrados_ganados = 0
    cerrados_perdidos = 0
    partidos_con_datos = 0

    for p in partidos:
        if p.rondas_jugadas not in (2, 3):
            continue
        partidos_con_datos += 1
        gano = p.ganador_id == jugador_id
        if p.rondas_jugadas == 2:
            if gano:
                rounds_ganados += 2
                barridas_hechas += 1
            else:
                rounds_perdidos += 2
                barridas_recibidas += 1
        else:
            if gano:
                rounds_ganados += 2
                rounds_perdidos += 1
                cerrados_ganados += 1
            else:
                rounds_ganados += 1
                rounds_perdidos += 2
                cerrados_perdidos += 1

    total_rounds = rounds_ganados + rounds_perdidos
    return {
        "partidos_con_datos_de_rondas": partidos_con_datos,
        "rounds_ganados": rounds_ganados,
        "rounds_perdidos": rounds_perdidos,
        "round_win_rate": round(rounds_ganados / total_rounds, 3) if total_rounds else None,
        "barridas_hechas": barridas_hechas,
        "barridas_recibidas": barridas_recibidas,
        "cerrados_ganados": cerrados_ganados,
        "cerrados_perdidos": cerrados_perdidos,
    }


def _stats_cinco_vidas(jugador_id, torneos_finalizados, nombres=None):
    """Quién te eliminó y a quiénes eliminaste vos, en el modo cinco_vidas.
    Para cada torneo de ese modo, se busca el partido puntual donde cada
    jugador perdió su última vida (obtener_partido_eliminacion) -- ahí el
    ganador de ESE partido puntual es quien lo eliminó."""
    torneos_cv = [t for t in torneos_finalizados if t.modo == "cinco_vidas"]
    eliminado_por = {}
    eliminaste_a = {}

    # Se trae TODO de una: las vidas de todos los torneos en una consulta, y
    # los partidos de todos los torneos en otra. Antes, esto pedía las vidas
    # por torneo MÁS un partido por cada jugador eliminado de cada torneo --
    # con unos pocos torneos ya eran decenas de consultas para armar un
    # solo perfil.
    ids_cv = [t.id for t in torneos_cv]
    vidas_por_torneo = torneo_jugador_repository.obtener_vidas_de_torneos(ids_cv)
    partidos_por_torneo = partido_repository.obtener_partidos_cinco_vidas_de_torneos(ids_cv)

    def _partido_donde_lo_eliminaron(partidos, jid):
        """El último partido que ese jugador perdió -- ahí perdió su última
        vida. Mismo criterio que la consulta que se hacía antes por
        separado (la más reciente por fecha_jugado)."""
        perdidos = [
            p for p in partidos
            if (p.jugador1_id == jid or p.jugador2_id == jid) and p.ganador_id != jid
        ]
        if not perdidos:
            return None
        return max(perdidos, key=lambda p: (p.fecha_jugado is not None, p.fecha_jugado))

    for t in torneos_cv:
        vidas_torneo = vidas_por_torneo.get(t.id, [])
        partidos_torneo = partidos_por_torneo.get(t.id, [])
        propio = next((f for f in vidas_torneo if f["jugador_id"] == jugador_id), None)

        if propio and propio["eliminado"]:
            partido_elim = _partido_donde_lo_eliminaron(partidos_torneo, jugador_id)
            if partido_elim:
                rival_id = partido_elim.ganador_id
                entrada = eliminado_por.setdefault(rival_id, {"jugador_id": rival_id, "veces": 0})
                entrada["veces"] += 1

        for f in vidas_torneo:
            if f["jugador_id"] == jugador_id or not f["eliminado"]:
                continue
            partido_elim = _partido_donde_lo_eliminaron(partidos_torneo, f["jugador_id"])
            if partido_elim and partido_elim.ganador_id == jugador_id:
                entrada = eliminaste_a.setdefault(f["jugador_id"], {"jugador_id": f["jugador_id"], "veces": 0})
                entrada["veces"] += 1

    nombres = nombres if nombres is not None else {j.id: j.nombre for j in jugador_repository.obtener_todos()}
    lista_eliminado_por = sorted(eliminado_por.values(), key=lambda f: -f["veces"])
    lista_eliminaste = sorted(eliminaste_a.values(), key=lambda f: -f["veces"])
    for d in lista_eliminado_por + lista_eliminaste:
        d["nombre"] = nombres.get(d["jugador_id"])

    return {
        "quien_te_elimino_mas": _todos_los_maximos(lista_eliminado_por, key=lambda f: f["veces"]),
        "a_quien_eliminaste_mas": _todos_los_maximos(lista_eliminaste, key=lambda f: f["veces"]),
        "eliminado_por_detalle": lista_eliminado_por,
        "eliminaste_detalle": lista_eliminaste,
    }
