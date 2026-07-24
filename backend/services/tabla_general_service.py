from repositories import torneo_repository, partido_repository, torneo_jugador_repository, jugador_repository
from services import tabla_service

PUNTOS_POR_PUESTO = {1: 8, 2: 7, 3: 6, 4: 4, 5: 2}  # puesto 6 en adelante -> 1 punto (default)


def _puntos_por_puesto(puesto):
    return PUNTOS_POR_PUESTO.get(puesto, 1)


# =========================================================
# Cálculo de puestos, uno por modo (misma idea, forma distinta de resolverla)
# =========================================================

def _puestos_todos_contra_todos(torneo_id):
    tabla = tabla_service.calcular_tabla_todos_contra_todos(torneo_id)
    return {fila["jugador_id"]: posicion + 1 for posicion, fila in enumerate(tabla)}


def _puestos_cinco_vidas(torneo_id):
    filas = torneo_jugador_repository.obtener_vidas_de_torneo(torneo_id)
    total = len(filas)
    puestos = {}
    for f in filas:
        if not f["eliminado"]:
            puestos[f["jugador_id"]] = 1  # el campeón nunca fue eliminado
        else:
            puestos[f["jugador_id"]] = total - f["orden_eliminacion"] + 1
    return puestos


def _puestos_grupos_eliminacion(torneo_id):
    partidos_elim = partido_repository.obtener_finalizados_por_torneo(torneo_id, "eliminacion", [])
    puestos = {}

    if partidos_elim:
        final_ronda = max(p.ronda for p in partidos_elim)
        final = next(p for p in partidos_elim if p.ronda == final_ronda)

        puestos[final.ganador_id] = 1
        perdedor_final = (
            final.jugador2_id if final.ganador_id == final.jugador1_id else final.jugador1_id
        )
        puestos[perdedor_final] = 2

        partidos_tercer = partido_repository.obtener_finalizados_por_torneo(torneo_id, "tercer_puesto", [])
        if partidos_tercer:
            tp = partidos_tercer[0]
            puestos[tp.ganador_id] = 3
            perdedor_tp = tp.jugador2_id if tp.ganador_id == tp.jugador1_id else tp.jugador1_id
            puestos[perdedor_tp] = 4

        ronda_cuartos = final_ronda - 2
        if ronda_cuartos >= 1:
            for p in partidos_elim:
                if p.ronda == ronda_cuartos:
                    perdedor = p.jugador2_id if p.ganador_id == p.jugador1_id else p.jugador1_id
                    puestos[perdedor] = 5

    # todos los demás participantes del torneo (no llegaron a cuartos) -> puesto 6, "resto"
    todos = torneo_jugador_repository.obtener_jugadores_de_torneo(torneo_id)
    for j in todos:
        puestos.setdefault(j["jugador_id"], 6)

    return puestos


def calcular_puestos(torneo):
    if torneo.modo == "todos_contra_todos":
        return _puestos_todos_contra_todos(torneo.id)
    elif torneo.modo == "cinco_vidas":
        return _puestos_cinco_vidas(torneo.id)
    elif torneo.modo == "grupos_eliminacion":
        return _puestos_grupos_eliminacion(torneo.id)
    return {}


# =========================================================
# Tabla general (ranking histórico entre torneos)
# =========================================================

def calcular_tabla_general(torneos_excluidos_ids=None):
    """
    Suma los puntos de puesto de cada torneo finalizado (salvo los excluidos).
    Desempata por: 1) puntos totales, 2) puntos de victoria (3 por cada
    partido ganado, sumando TODOS los torneos incluidos), 3) win rate global.
    """
    torneos_excluidos_ids = torneos_excluidos_ids or []
    torneos = torneo_repository.obtener_finalizados(torneos_excluidos_ids)
    torneos_incluidos_ids = [t.id for t in torneos]

    acumulado = {}
    for torneo in torneos:
        puestos = calcular_puestos(torneo)
        for jugador_id, puesto in puestos.items():
            entrada = acumulado.setdefault(
                jugador_id, {"jugador_id": jugador_id, "puntos": 0, "torneos_jugados": 0}
            )
            entrada["puntos"] += _puntos_por_puesto(puesto)
            entrada["torneos_jugados"] += 1

    # Desempate: estadísticas de partidos individuales, sumando TODOS los
    # torneos incluidos (no solo los que cada jugador jugó de a uno)
    partidos = partido_repository.obtener_finalizados_por_torneos(torneos_incluidos_ids)
    stats = {}
    for p in partidos:
        for jugador_id in (p.jugador1_id, p.jugador2_id):
            stats.setdefault(jugador_id, {"pj": 0, "pg": 0})
            stats[jugador_id]["pj"] += 1
        if p.ganador_id in stats:
            stats[p.ganador_id]["pg"] += 1

    nombres = {j["id"]: j["nombre"] for j in jugador_repository.obtener_todos()}

    resultado = []
    for jugador_id, entrada in acumulado.items():
        pj = stats.get(jugador_id, {"pj": 0, "pg": 0})["pj"]
        pg = stats.get(jugador_id, {"pj": 0, "pg": 0})["pg"]
        resultado.append({
            "jugador_id": jugador_id,
            "nombre": nombres.get(jugador_id),
            "puntos": entrada["puntos"],
            "torneos_jugados": entrada["torneos_jugados"],
            "puntos_victoria": pg * 3,
            "partidos_jugados": pj,
            "partidos_ganados": pg,
            "win_rate": round(pg / pj, 3) if pj > 0 else 0,
        })

    resultado.sort(key=lambda f: (-f["puntos"], -f["puntos_victoria"], -f["win_rate"]))
    return resultado