import math

from repositories import partido_repository, torneo_repository, jugador_repository

ANCLA_P = 1.0  # fuerza fija de un rival virtual, ancla la escala y evita que alguien invicto/sin victorias rompa la convergencia
ITERACIONES_MAXIMAS = 300
TOLERANCIA_CONVERGENCIA = 1e-9


def calcular_ratings():
    """
    Rating de cada jugador basado en Bradley-Terry sobre TODO el
    historial de partidos reales (excluye repechaje/desempate, mismo
    criterio que el resto de las estadísticas del proyecto) -- a
    diferencia de Elo, no pondera lo reciente sobre lo viejo: busca un
    solo número por jugador que mejor explique el conjunto completo de
    resultados a la vez.

    Se presenta en escala tipo Elo (1500 = fuerza de referencia) para
    que sea legible, pero el cálculo de fondo es Bradley-Terry.

    Devuelve [{jugador_id, nombre, rating, partidos_jugados}] ordenado
    de mayor a menor rating. Jugadores sin ningún partido real no
    aparecen (no hay datos para estimarles nada).
    """
    torneos_ids = [t.id for t in torneo_repository.obtener_finalizados()]
    partidos = partido_repository.obtener_finalizados_por_torneos(torneos_ids)

    resultados = [
        (p.ganador_id, p.jugador2_id if p.ganador_id == p.jugador1_id else p.jugador1_id)
        for p in partidos
    ]

    fuerzas = _bradley_terry(resultados)

    partidos_jugados = {}
    for ganador, perdedor in resultados:
        partidos_jugados[ganador] = partidos_jugados.get(ganador, 0) + 1
        partidos_jugados[perdedor] = partidos_jugados.get(perdedor, 0) + 1

    nombres = {j.id: j.nombre for j in jugador_repository.obtener_todos()}

    filas = [
        {
            "jugador_id": jugador_id,
            "nombre": nombres.get(jugador_id),
            "rating": _p_a_elo(p_i),
            "partidos_jugados": partidos_jugados.get(jugador_id, 0),
        }
        for jugador_id, p_i in fuerzas.items()
    ]
    filas.sort(key=lambda f: -f["rating"])
    return filas


def calcular_probabilidades_resultados():
    """
    Para cada partido real del historial, la probabilidad que el modelo
    (con las fuerzas finales, ya ajustadas con todo el historial) le
    daba al GANADOR de haber ganado -- sirve para medir qué tan
    sorpresivo fue cada resultado. Cuanto más baja la probabilidad, más
    sorpresivo. Comparten esta base tanto 'resultado más sorpresivo de
    la historia' (general) como 'mejor victoria'/'peor caída' (de cada
    jugador).

    Devuelve [{partido_id, torneo_id, torneo_nombre, ganador_id,
    perdedor_id, probabilidad_ganador}].
    """
    torneos = torneo_repository.obtener_finalizados()
    torneos_por_id = {t.id: t for t in torneos}
    partidos = partido_repository.obtener_finalizados_por_torneos([t.id for t in torneos])

    resultados = [
        (p.ganador_id, p.jugador2_id if p.ganador_id == p.jugador1_id else p.jugador1_id)
        for p in partidos
    ]
    fuerzas = _bradley_terry(resultados)

    filas = []
    for p in partidos:
        ganador = p.ganador_id
        perdedor = p.jugador2_id if p.ganador_id == p.jugador1_id else p.jugador1_id
        p_g, p_p = fuerzas.get(ganador), fuerzas.get(perdedor)
        if p_g is None or p_p is None:
            continue
        torneo = torneos_por_id.get(p.torneo_id)
        filas.append({
            "partido_id": p.id,
            "torneo_id": p.torneo_id,
            "torneo_nombre": torneo.nombre if torneo else None,
            "ganador_id": ganador,
            "perdedor_id": perdedor,
            "probabilidad_ganador": round(p_g / (p_g + p_p), 4),
        })
    return filas


def _bradley_terry(resultados):
    """
    resultados: lista de (ganador_id, perdedor_id).
    Devuelve {jugador_id: fuerza} (siempre positiva) vía el algoritmo MM
    de Hunter (2004) -- el estándar para ajustar un modelo Bradley-Terry
    sin depender de librerías externas. Cada jugador real recibe además
    1 victoria y 1 derrota virtuales contra un rival ficticio de fuerza
    fija (ANCLA_P): sin esto, alguien invicto "querría" una fuerza
    infinita y el cálculo no converge, y de paso esto fija la escala de
    una vez (no hace falta normalizar aparte).
    """
    jugadores = set()
    for ganador, perdedor in resultados:
        jugadores.add(ganador)
        jugadores.add(perdedor)

    if not jugadores:
        return {}

    n = {i: {} for i in jugadores}  # n[i][j] = cantidad de partidos entre i y j
    w = {i: 0 for i in jugadores}  # victorias reales
    for ganador, perdedor in resultados:
        w[ganador] += 1
        n[ganador][perdedor] = n[ganador].get(perdedor, 0) + 1
        n[perdedor][ganador] = n[perdedor].get(ganador, 0) + 1

    p = {i: 1.0 for i in jugadores}

    for _ in range(ITERACIONES_MAXIMAS):
        p_nuevo = {}
        for i in jugadores:
            victorias = w[i] + 1  # +1 victoria virtual contra el ancla
            denominador = 2 / (p[i] + ANCLA_P)  # 2 partidos virtuales contra el ancla
            for j, n_ij in n[i].items():
                denominador += n_ij / (p[i] + p[j])
            p_nuevo[i] = victorias / denominador if denominador > 0 else p[i]

        cambio = max(abs(p_nuevo[i] - p[i]) for i in jugadores)
        p = p_nuevo
        if cambio < TOLERANCIA_CONVERGENCIA:
            break

    return p


def _p_a_elo(p_i):
    return round(1500 + 400 * math.log10(p_i))
