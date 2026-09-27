from repositories import torneo_repository, partido_repository, torneo_jugador_repository, jugador_repository
from services import tabla_service

PUNTOS_POR_PUESTO = {1: 8, 2: 7, 3: 6, 4: 4, 5: 2}  # puesto 6 en adelante -> 1 punto (default)

EMOJI_POR_PUESTO = {1: "🥇", 2: "🥈", 3: "🥉", 4: "4️⃣", 5: "8️⃣"}
EMOJI_PARTICIPACION = "🎮"  # puesto 6 en adelante


def _puntos_por_puesto(puesto):
    return PUNTOS_POR_PUESTO.get(puesto, 1)


def emoji_por_puesto(puesto):
    """Pública a propósito: las tablas de cada torneo usan el mismo emoji
    que las insignias del ranking general, así el 🥇 significa siempre lo
    mismo en toda la app."""
    return EMOJI_POR_PUESTO.get(puesto, EMOJI_PARTICIPACION)


def _emoji_por_puesto(puesto):
    return emoji_por_puesto(puesto)


# =========================================================
# Cálculo de puestos, uno por modo (misma idea, forma distinta de resolverla)
# =========================================================

def _puestos_todos_contra_todos(torneo_id, jugadores_prefetch=None, partidos_prefetch=None):
    """
    Ranking 'denso': todos los empatados en puntos comparten el mismo
    puesto, y el próximo grupo de puntos distinto pasa al puesto siguiente
    sin saltar números (no es 1,1,1,4 -- es 1,1,1,2). Ej: si 9 de 10
    jugadores empatan en la cima, los 9 son 1° y el restante es 2°, no 10°.
    """
    tabla = tabla_service.calcular_tabla_todos_contra_todos(
        torneo_id, jugadores_prefetch=jugadores_prefetch, partidos_prefetch=partidos_prefetch
    )
    puestos = {}
    puesto_actual = 0
    puntos_anterior = None
    for fila in tabla:
        if fila["puntos"] != puntos_anterior:
            puesto_actual += 1
            puntos_anterior = fila["puntos"]
        puestos[fila["jugador_id"]] = puesto_actual
    return puestos


def _puestos_rey_de_la_cancha(torneo_id, vidas_prefetch=None, partidos_prefetch=None, nombres_prefetch=None):
    """El cálculo completo (racha², desempate por posición) vive en
    tabla_service.calcular_tabla_rey_de_la_cancha -- acá solo se extrae el
    mapeo jugador_id -> puesto que necesita la tabla general."""
    tabla = tabla_service.calcular_tabla_rey_de_la_cancha(
        torneo_id, vidas_prefetch=vidas_prefetch, partidos_prefetch=partidos_prefetch, nombres_prefetch=nombres_prefetch
    )
    return {f["jugador_id"]: f["puesto"] for f in tabla}


# Mientras el torneo no terminó, los que todavía no tienen puesto quedan
# todos acá (todavía no se sabe hasta dónde llega cada uno).
PUESTO_SIN_DEFINIR_EN_CURSO = 6


def _puestos_grupos_eliminacion(torneo, jugadores_prefetch=None, partidos_prefetch=None,
                                grupos_prefetch=None, vidas_prefetch=None, nombres_prefetch=None):
    """
    Puestos densos por instancia alcanzada. Criterio general: ante la duda
    se da de más, no de menos -- los que llegan a la misma instancia
    comparten el MEJOR puesto de esa instancia, y la instancia siguiente
    toma el puesto inmediato (1,1,2 y no 1,1,3), igual que el ranking
    denso de todos contra todos.

    1. El cuadro: campeón 1, finalista 2, tercer puesto 3 y 4, y cada ronda
       anterior es una instancia más (cuartos, octavos...).
    2. Los que no clasificaron, por su DISTANCIA AL CORTE en su grupo: el
       primer eliminado de cada grupo toma el puesto siguiente al cuadro,
       el segundo eliminado el que sigue, etc. Se mide contra el corte y
       no por la posición cruda porque con largest-remainder dos grupos
       pueden clasificar distinta cantidad (el 3° de uno pudo clasificar
       y el 3° de otro no). Empatados en puntos dentro del grupo comparten
       la mejor distancia.

    Ej: 11 jugadores, grupos de 5 y 6, pasan 2 por grupo -> 1° a 4° del
    cuadro; los dos 3° de grupo, 5°; los 4° de grupo, 6°; y así.

    El paso 2 solo corre con el torneo finalizado: antes, un jugador sin
    puesto puede ser alguien que sigue vivo en el cuadro.
    """
    torneo_id = torneo.id
    if partidos_prefetch is not None:
        partidos_elim = [p for p in partidos_prefetch if p.fase == "eliminacion"]
        partidos_tercer = [p for p in partidos_prefetch if p.fase == "tercer_puesto"]
    else:
        partidos_elim = partido_repository.obtener_finalizados_por_torneo(torneo_id, "eliminacion", [])
        partidos_tercer = partido_repository.obtener_finalizados_por_torneo(torneo_id, "tercer_puesto", [])

    puestos = {}

    if partidos_elim:
        final_ronda = max(p.ronda for p in partidos_elim)
        final = next(p for p in partidos_elim if p.ronda == final_ronda)

        puestos[final.ganador_id] = 1
        puestos[_perdedor(final)] = 2

        if partidos_tercer:
            tp = partidos_tercer[0]
            puestos[tp.ganador_id] = 3
            puestos[_perdedor(tp)] = 4

        # Cada ronda anterior a la final es una instancia: sus perdedores
        # comparten el puesto siguiente al último asignado. Los de semis ya
        # quedaron ubicados por el tercer puesto, así que esa ronda no suma
        # nada -- y si por algún motivo no hubo tercer puesto, los dos
        # semifinalistas comparten el 3 en vez de quedar sin ubicar.
        for ronda in range(final_ronda - 1, 0, -1):
            perdedores = [
                _perdedor(p) for p in partidos_elim
                if p.ronda == ronda and _perdedor(p) not in puestos
            ]
            if perdedores:
                siguiente = max(puestos.values()) + 1
                for jugador_id in perdedores:
                    puestos[jugador_id] = siguiente

    todos = jugadores_prefetch if jugadores_prefetch is not None else torneo_jugador_repository.obtener_jugadores_de_torneo(torneo_id)

    if torneo.estado != "finalizado":
        for j in todos:
            puestos.setdefault(j["jugador_id"], PUESTO_SIN_DEFINIR_EN_CURSO)
        return puestos

    distancias = _distancias_al_corte(
        torneo, set(puestos), grupos_prefetch=grupos_prefetch, partidos_prefetch=partidos_prefetch,
        vidas_prefetch=vidas_prefetch, nombres_prefetch=nombres_prefetch,
    )
    base = max(puestos.values(), default=0) + 1
    for jugador_id, distancia in distancias.items():
        puestos[jugador_id] = base + distancia - 1

    # Red de seguridad: alguien del torneo que no está en el cuadro ni en
    # ningún grupo (no debería pasar) comparte la última instancia en vez
    # de abrir una más abajo.
    ultimo = max(puestos.values(), default=1)
    for j in todos:
        puestos.setdefault(j["jugador_id"], ultimo)

    return puestos


def _perdedor(partido):
    return partido.jugador2_id if partido.ganador_id == partido.jugador1_id else partido.jugador1_id


def _distancias_al_corte(torneo, clasificados_ids, grupos_prefetch=None, partidos_prefetch=None,
                         vidas_prefetch=None, nombres_prefetch=None):
    """{jugador_id: distancia} para cada jugador que no clasificó: 1 para
    el primer eliminado de su grupo, 2 para el segundo, etc. (denso: los
    empatados en puntos comparten la mejor).

    El orden sale de tabla_service.calcular_tabla_grupo, la misma tabla que
    decide los clasificados -- así la tabla de un grupo y el puesto final
    nunca se contradicen, sea el grupo todos contra todos o rey de la
    cancha (en los dos, 'puntos' ordena la tabla).

    Con los *_prefetch no hace ninguna consulta; sin ellos, trae lo de este
    torneo en una tanda (se usa al mirar un torneo puntual)."""
    if grupos_prefetch is None:
        grupos_prefetch = torneo_jugador_repository.obtener_jugadores_de_grupos_de_torneos([torneo.id]).get(torneo.id, {})
    if partidos_prefetch is None:
        partidos_prefetch = partido_repository.obtener_finalizados_por_torneo(torneo.id, "grupos", [])
    es_rey = torneo.formato_grupos == "rey_de_la_cancha"
    if es_rey and vidas_prefetch is None:
        vidas_prefetch = torneo_jugador_repository.obtener_vidas_de_torneo(torneo.id)
    if es_rey and nombres_prefetch is None:
        nombres_prefetch = {j.id: j.nombre for j in jugador_repository.obtener_todos()}

    distancias = {}
    for grupo_id, jugadores_grupo in grupos_prefetch.items():
        tabla = tabla_service.calcular_tabla_grupo(
            grupo_id, torneo_prefetch=torneo, jugadores_prefetch=jugadores_grupo,
            partidos_prefetch=partidos_prefetch, vidas_prefetch=vidas_prefetch,
            nombres_prefetch=nombres_prefetch,
        )
        afuera = [f for f in tabla if f["jugador_id"] not in clasificados_ids]
        puntos_distintos = sorted({f["puntos"] for f in afuera}, reverse=True)
        for f in afuera:
            distancias[f["jugador_id"]] = puntos_distintos.index(f["puntos"]) + 1
    return distancias


def calcular_puestos(torneo, jugadores_prefetch=None, partidos_prefetch=None, vidas_prefetch=None, nombres_prefetch=None,
                     grupos_prefetch=None):
    """
    Calcula el puesto de cada jugador en un torneo, según su modo.

    Los *_prefetch son opcionales -- pensados para cuando se recorren
    MUCHOS torneos seguidos (como en calcular_tabla_general): en vez de
    que cada torneo dispare sus propias consultas (jugadores, partidos,
    vidas), se le pasan los datos ya traídos de antes en una sola tanda.
    Sin pasar nada, funciona exactamente igual que antes -- consulta
    fresco, para cuando se pide el puesto de un solo torneo puntual.

    grupos_prefetch ({grupo_id: [jugadores]}) solo lo usa grupos +
    eliminación, para ubicar a los que no clasificaron.
    """
    if torneo.modo == "todos_contra_todos":
        return _puestos_todos_contra_todos(torneo.id, jugadores_prefetch=jugadores_prefetch, partidos_prefetch=partidos_prefetch)
    elif torneo.modo == "rey_de_la_cancha":
        return _puestos_rey_de_la_cancha(torneo.id, vidas_prefetch=vidas_prefetch, partidos_prefetch=partidos_prefetch, nombres_prefetch=nombres_prefetch)
    elif torneo.modo == "grupos_eliminacion":
        return _puestos_grupos_eliminacion(
            torneo, jugadores_prefetch=jugadores_prefetch, partidos_prefetch=partidos_prefetch,
            grupos_prefetch=grupos_prefetch, vidas_prefetch=vidas_prefetch, nombres_prefetch=nombres_prefetch,
        )
    return {}


# =========================================================
# Tabla general (ranking histórico entre torneos)
# =========================================================

def calcular_tabla_general(
    torneos_excluidos_ids=None, incluir_movimiento=True,
    torneos_prefetch=None, partidos_prefetch=None, nombres_prefetch=None, jugadores_por_torneo_prefetch=None,
):
    """
    Suma los puntos de puesto de cada torneo finalizado (salvo los excluidos).
    Desempata por: 1) puntos totales, 2) puntos de victoria (3 por cada
    partido ganado, sumando TODOS los torneos incluidos), 3) win rate global.

    Si incluir_movimiento=True (default), cada fila trae además
    'movimiento': cuánto subió/bajó cada jugador respecto a la 'instancia
    anterior' -- la misma tabla, pero sin contar el torneo más reciente de
    los que están incluidos ahora mismo. Un jugador que no tenía puesto en
    esa instancia anterior (su primer torneo fue justo el más reciente)
    queda marcado como 'nuevo', no como que subió una cantidad arbitraria
    de puestos.

    Nota de rendimiento: TODO lo que hace falta para calcular el puesto
    de cada torneo (jugadores, partidos, vidas, integrantes de cada grupo) se trae acá
    en una sola tanda para TODOS los torneos a la vez, y se le pasa ya
    listo a cada uno -- en vez de que cada torneo dispare sus propias
    consultas por su cuenta. Contra una base remota, con esto la
    cantidad de consultas deja de crecer con la cantidad de torneos.

    Los *_prefetch son opcionales -- pensados para cuando quien llama
    (como las estadísticas generales) ya tiene estos datos en memoria
    (mismo set de torneos, sin exclusiones) y no hace falta volver a
    pedirlos. Sin pasar nada, se comporta exactamente igual que antes.
    """
    torneos_excluidos_ids = torneos_excluidos_ids or []
    if torneos_prefetch is not None:
        torneos = [t for t in torneos_prefetch if t.id not in torneos_excluidos_ids]
    else:
        torneos = torneo_repository.obtener_finalizados(torneos_excluidos_ids)
    torneos = sorted(torneos, key=lambda t: t.fecha)  # cronológico, para que las insignias se lean en orden
    torneos_incluidos_ids = [t.id for t in torneos]

    if partidos_prefetch is not None:
        ids_incluidos = set(torneos_incluidos_ids)
        partidos = [p for p in partidos_prefetch if p.torneo_id in ids_incluidos]
    else:
        partidos = partido_repository.obtener_finalizados_por_torneos(torneos_incluidos_ids)

    nombres = nombres_prefetch if nombres_prefetch is not None else {j.id: j.nombre for j in jugador_repository.obtener_todos()}
    jugadores_por_torneo = (
        jugadores_por_torneo_prefetch if jugadores_por_torneo_prefetch is not None
        else torneo_jugador_repository.obtener_jugadores_de_torneos(torneos_incluidos_ids)
    )
    # Las vidas hacen falta en los torneos rey de la cancha Y en los de
    # grupos jugados a rey de la cancha (para ordenar a los que no
    # clasificaron): se piden todas en la misma consulta.
    vidas_por_torneo = torneo_jugador_repository.obtener_vidas_de_torneos([
        t.id for t in torneos
        if t.modo == "rey_de_la_cancha"
        or (t.modo == "grupos_eliminacion" and t.formato_grupos == "rey_de_la_cancha")
    ])
    grupos_por_torneo = torneo_jugador_repository.obtener_jugadores_de_grupos_de_torneos(
        [t.id for t in torneos if t.modo == "grupos_eliminacion"]
    )
    partidos_por_torneo = {}
    for p in partidos:
        partidos_por_torneo.setdefault(p.torneo_id, []).append(p)

    puestos_por_torneo = {
        t.id: calcular_puestos(
            t,
            jugadores_prefetch=jugadores_por_torneo.get(t.id, []),
            partidos_prefetch=partidos_por_torneo.get(t.id, []),
            vidas_prefetch=vidas_por_torneo.get(t.id),
            nombres_prefetch=nombres,
            grupos_prefetch=grupos_por_torneo.get(t.id),
        )
        for t in torneos
    }

    resultado = _armar_tabla(torneos, puestos_por_torneo, partidos, nombres)

    if incluir_movimiento and torneos:
        torneo_mas_reciente = torneos[-1]  # ya viene ordenado cronológico
        torneos_anteriores = torneos[:-1]
        partidos_anteriores = [p for p in partidos if p.torneo_id != torneo_mas_reciente.id]
        resultado_anterior = _armar_tabla(torneos_anteriores, puestos_por_torneo, partidos_anteriores, nombres)
        puesto_anterior_por_jugador = {f["jugador_id"]: f["puesto"] for f in resultado_anterior}

        for fila in resultado:
            puesto_antes = puesto_anterior_por_jugador.get(fila["jugador_id"])
            if puesto_antes is None:
                fila["movimiento"] = {"tipo": "nuevo", "cantidad": 0}
            else:
                delta = puesto_antes - fila["puesto"]
                if delta > 0:
                    fila["movimiento"] = {"tipo": "subio", "cantidad": delta}
                elif delta < 0:
                    fila["movimiento"] = {"tipo": "bajo", "cantidad": abs(delta)}
                else:
                    fila["movimiento"] = {"tipo": "igual", "cantidad": 0}
    else:
        for fila in resultado:
            fila["movimiento"] = None

    return resultado


def _armar_tabla(torneos, puestos_por_torneo, partidos, nombres):
    """Arma la tabla (puntos, ranking) a partir de datos YA calculados/
    consultados -- no hace ninguna consulta nueva a la base. Se usa dos
    veces (ranking actual, y 'antes del último torneo') sin repetir
    ningún viaje a la base entre una y otra."""
    acumulado = {}
    for torneo in torneos:
        puestos = puestos_por_torneo[torneo.id]
        for jugador_id, puesto in puestos.items():
            entrada = acumulado.setdefault(
                jugador_id, {"jugador_id": jugador_id, "puntos": 0, "torneos_jugados": 0, "insignias": []}
            )
            entrada["puntos"] += _puntos_por_puesto(puesto)
            entrada["torneos_jugados"] += 1
            entrada["insignias"].append({
                "torneo_id": torneo.id,
                "torneo_nombre": torneo.nombre,
                "puesto": puesto,
                "emoji": _emoji_por_puesto(puesto),
            })

    stats = {}
    for p in partidos:
        for jugador_id in (p.jugador1_id, p.jugador2_id):
            stats.setdefault(jugador_id, {"pj": 0, "pg": 0})
            stats[jugador_id]["pj"] += 1
        if p.ganador_id in stats:
            stats[p.ganador_id]["pg"] += 1

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
            "partidos_perdidos": pj - pg,
            "win_rate": round(pg / pj, 3) if pj > 0 else 0,
            "insignias": entrada["insignias"],
        })

    resultado.sort(key=lambda f: (-f["puntos"], -f["puntos_victoria"], -f["win_rate"]))

    # Puesto denso sobre la terna completa: comparten puesto solo si
    # empatan en puntos, puntos_victoria Y win_rate a la vez -- no alcanza
    # con empatar en uno para compartir posición.
    puesto_actual = 0
    clave_anterior = None
    for fila in resultado:
        clave = (fila["puntos"], fila["puntos_victoria"], fila["win_rate"])
        if clave != clave_anterior:
            puesto_actual += 1
            clave_anterior = clave
        fila["puesto"] = puesto_actual

    return resultado
