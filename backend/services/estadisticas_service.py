from repositories import (
    torneo_repository, partido_repository, jugador_repository,
    peleador_repository, torneo_jugador_repository,
)
from services import tabla_general_service


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

    return {
        "jugador_id": jugador_id,
        "nombre": jugador.nombre,
        "resumen_general": _resumen_general(jugador_id, partidos),
        "ultimos_resultados": _ultimos_resultados(jugador_id, partidos),
        "rivales": _stats_rivales(jugador_id, partidos),
        "peleadores": _stats_peleadores(jugador_id, partidos),
        "peleadores_rivales": _stats_peleadores_rivales(jugador_id, partidos),
        "rachas": _stats_rachas(jugador_id, partidos),
        "rounds": _stats_rounds(jugador_id, partidos),
        "torneos": _stats_torneos(jugador_id, torneos_finalizados, torneos_todos),
        "cinco_vidas": _stats_cinco_vidas(jugador_id, torneos_finalizados),
        "veces_en_repechaje_o_desempate": torneo_jugador_repository.contar_repechajes_y_desempates(jugador_id),
    }


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


def _stats_rivales(jugador_id, partidos):
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

    nombres = {j.id: j.nombre for j in jugador_repository.obtener_todos()}
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


def _stats_peleadores(jugador_id, partidos):
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

    nombres_peleador = {pl.id: pl.nombre for pl in peleador_repository.obtener_todos()}
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


def _stats_peleadores_rivales(jugador_id, partidos):
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

    nombres_peleador = {pl.id: pl.nombre for pl in peleador_repository.obtener_todos()}
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

    mejor_puesto = None
    veces_campeon = 0
    suma_puestos = 0
    cantidad_puestos = 0
    for t in torneos_finalizados:
        puesto = tabla_general_service.calcular_puestos(t).get(jugador_id)
        if puesto is None:
            continue
        suma_puestos += puesto
        cantidad_puestos += 1
        if puesto == 1:
            veces_campeon += 1
        if mejor_puesto is None or puesto < mejor_puesto["puesto"]:
            mejor_puesto = {"torneo_id": t.id, "nombre": t.nombre, "puesto": puesto}

    return {
        "torneos_jugados_por_modo": por_modo,
        "torneos_jugados_total": len(torneos_todos),
        "veces_campeon": veces_campeon,
        "mejor_puesto_historico": mejor_puesto,
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


def _stats_cinco_vidas(jugador_id, torneos_finalizados):
    """Quién te eliminó y a quiénes eliminaste vos, en el modo cinco_vidas.
    Para cada torneo de ese modo, se busca el partido puntual donde cada
    jugador perdió su última vida (obtener_partido_eliminacion) -- ahí el
    ganador de ESE partido puntual es quien lo eliminó."""
    torneos_cv = [t for t in torneos_finalizados if t.modo == "cinco_vidas"]
    eliminado_por = {}
    eliminaste_a = {}

    for t in torneos_cv:
        vidas_torneo = torneo_jugador_repository.obtener_vidas_de_torneo(t.id)
        propio = next((f for f in vidas_torneo if f["jugador_id"] == jugador_id), None)

        if propio and propio["eliminado"]:
            partido_elim = partido_repository.obtener_partido_eliminacion(t.id, jugador_id)
            if partido_elim:
                rival_id = partido_elim.ganador_id
                entrada = eliminado_por.setdefault(rival_id, {"jugador_id": rival_id, "veces": 0})
                entrada["veces"] += 1

        for f in vidas_torneo:
            if f["jugador_id"] == jugador_id or not f["eliminado"]:
                continue
            partido_elim = partido_repository.obtener_partido_eliminacion(t.id, f["jugador_id"])
            if partido_elim and partido_elim.ganador_id == jugador_id:
                entrada = eliminaste_a.setdefault(f["jugador_id"], {"jugador_id": f["jugador_id"], "veces": 0})
                entrada["veces"] += 1

    nombres = {j.id: j.nombre for j in jugador_repository.obtener_todos()}
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
