from datetime import date

from repositories import (
    torneo_repository, partido_repository, torneo_jugador_repository, jugador_repository,
    configuracion_general_repository,
)
from services import tabla_general_service, rating_service, estadisticas_config_service

MIN_PARTIDOS_PARA_RIVALIDAD = 3  # para "rivalidad más pareja" y "mayor padreada" -- un 1-0 no cuenta como nada
TOP_N = 5


def _top_n_con_empates(lista, key, n=TOP_N):
    """Devuelve los primeros N valores DISTINTOS de key (orden
    descendente), incluyendo TODOS los que empatan en cada valor -- por
    eso puede devolver más de N filas si hay empates en el último
    puesto. Mismo criterio de 'nunca decidir un empate arbitrariamente'
    que se usa en el resto del proyecto."""
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


def actualizar_proximo_torneo(fecha):
    """fecha=None borra el valor (vuelve todo a la normalidad)."""
    configuracion_general_repository.actualizar_fecha_proximo_torneo(fecha)


def actualizar_descripcion_inicio(descripcion):
    configuracion_general_repository.actualizar_descripcion_inicio(descripcion)


def actualizar_descripcion_tablas(descripcion):
    configuracion_general_repository.actualizar_descripcion_tablas(descripcion)


def actualizar_nombre_club(nombre):
    configuracion_general_repository.actualizar_nombre_club((nombre or "").strip() or None)


def actualizar_tile(nombre_tile, visible):
    configuracion_general_repository.actualizar_tile(nombre_tile, visible)


def obtener_nombre_club():
    """Getter liviano -- lo usa CADA página (el wordmark del header), no
    solo Inicio, así que no arma todo el resto de estadísticas generales
    para esto."""
    return configuracion_general_repository.obtener_nombre_club() or "App del Torneo"


def obtener_estadisticas_generales():
    fecha_ultimo = torneo_repository.obtener_fecha_ultimo_torneo()
    dias_desde_ultimo = (date.today() - fecha_ultimo).days if fecha_ultimo else None

    # "Próximo torneo": lo carga el organizador a mano (Configuración). Si
    # hay una fecha cargada y todavía no llegó, el conteo de Inicio muestra
    # la cuenta regresiva en vez de 'días desde el último' -- apenas esa
    # fecha pasa (haya torneo real o no), vuelve solo a la normalidad, sin
    # que haga falta 'desactivarlo' a mano.
    config = configuracion_general_repository.obtener()
    fecha_proximo = config["fecha_proximo_torneo"]
    modo = "ultimo"
    dias_para_proximo = None
    if fecha_proximo and fecha_proximo >= date.today():
        modo = "proximo"
        dias_para_proximo = (fecha_proximo - date.today()).days

    info_proximo = {
        "modo": modo,
        "fecha_proximo_torneo": fecha_proximo.isoformat() if fecha_proximo else None,
        "dias_para_proximo_torneo": dias_para_proximo,
        "descripcion_inicio": config["descripcion_inicio"],
        "descripcion_tablas": config["descripcion_tablas"],
        "nombre_club": config["nombre_club"] or "App del Torneo",
        "mostrar_tile_tablas": bool(config["mostrar_tile_tablas"]),
        "mostrar_tile_torneos": bool(config["mostrar_tile_torneos"]),
        "mostrar_tile_jugadores": bool(config["mostrar_tile_jugadores"]),
        "mostrar_tile_peleadores": bool(config["mostrar_tile_peleadores"]),
    }

    torneos = torneo_repository.obtener_finalizados()
    nombres = {j.id: j.nombre for j in jugador_repository.obtener_todos()}

    if not torneos:
        return {
            **info_proximo,
            "fecha_ultimo_torneo": None,
            "dias_desde_ultimo_torneo": None,
            "total_torneos": 0,
            "total_partidos": 0,
            "cantidad_por_modo": {},
            "promedio_jugadores_por_torneo": None,
            "top_torneos_mas_jugadores": [],
            "top_torneos_mas_partidos": [],
            "top_rivalidades_mas_frecuentes": [],
            "top_rivalidades_mas_parejas": [],
            "top_padreadas": [],
            "top_apariciones_podio": [],
            "top_resultados_sorpresivos": [],
            "distancia_rating_primero_ultimo": None,
        }

    partidos = partido_repository.obtener_finalizados_por_torneos([t.id for t in torneos])

    cantidad_por_modo = {}
    for t in torneos:
        cantidad_por_modo[t.modo] = cantidad_por_modo.get(t.modo, 0) + 1

    jugadores_por_torneo = {t.id: torneo_jugador_repository.obtener_jugadores_de_torneo(t.id) for t in torneos}
    top_torneos_mas_jugadores = _top_n_con_empates(
        [{"torneo_id": t.id, "torneo_nombre": t.nombre, "cantidad_jugadores": len(jugadores_por_torneo[t.id])} for t in torneos],
        key=lambda f: f["cantidad_jugadores"],
    )

    partidos_por_torneo = {}
    for p in partidos:
        partidos_por_torneo[p.torneo_id] = partidos_por_torneo.get(p.torneo_id, 0) + 1
    top_torneos_mas_partidos = _top_n_con_empates(
        [{"torneo_id": t.id, "torneo_nombre": t.nombre, "cantidad_partidos": partidos_por_torneo.get(t.id, 0)} for t in torneos],
        key=lambda f: f["cantidad_partidos"],
    )

    promedio_jugadores = (
        sum(len(v) for v in jugadores_por_torneo.values()) / len(jugadores_por_torneo)
        if jugadores_por_torneo else None
    )

    # Rivalidades: cuántas veces se enfrentó cada par, y el récord entre ellos
    conteo_par = {}
    registro_par = {}  # frozenset -> {jugador_id: victorias}
    for p in partidos:
        clave = frozenset({p.jugador1_id, p.jugador2_id})
        conteo_par[clave] = conteo_par.get(clave, 0) + 1
        registro_par.setdefault(clave, {})
        registro_par[clave][p.ganador_id] = registro_par[clave].get(p.ganador_id, 0) + 1

    top_rivalidades_mas_frecuentes = _top_n_con_empates(
        [{"jugadores": sorted(nombres.get(j, "?") for j in clave), "veces": veces} for clave, veces in conteo_par.items()],
        key=lambda f: f["veces"],
    )

    parejas_con_record = []
    for clave, reg in registro_par.items():
        ids = list(clave)
        if len(ids) < 2:
            continue
        v1, v2 = reg.get(ids[0], 0), reg.get(ids[1], 0)
        total = v1 + v2
        if total < MIN_PARTIDOS_PARA_RIVALIDAD:
            continue
        parejas_con_record.append({
            "jugadores": [nombres.get(ids[0]), nombres.get(ids[1])],
            "record": f"{v1}-{v2}",
            "diferencia": abs(v1 - v2),
        })

    top_rivalidades_mas_parejas = _top_n_con_empates(parejas_con_record, key=lambda f: -f["diferencia"])
    top_padreadas = _top_n_con_empates(parejas_con_record, key=lambda f: f["diferencia"])

    # Apariciones en podio (top 3) a lo largo de toda la historia
    apariciones_podio = {}
    for t in torneos:
        puestos = tabla_general_service.calcular_puestos(t)
        for jugador_id, puesto in puestos.items():
            if puesto <= 3:
                apariciones_podio[jugador_id] = apariciones_podio.get(jugador_id, 0) + 1
    top_apariciones_podio = _top_n_con_empates(
        [{"jugador_id": jid, "nombre": nombres.get(jid), "apariciones": c} for jid, c in apariciones_podio.items()],
        key=lambda f: f["apariciones"],
    )

    # Resultado más sorpresivo (con el rating final ya ajustado)
    probabilidades = rating_service.calcular_probabilidades_resultados()
    for f in probabilidades:
        f["ganador_nombre"] = nombres.get(f["ganador_id"])
        f["perdedor_nombre"] = nombres.get(f["perdedor_id"])
    top_resultados_sorpresivos = _top_n_con_empates(probabilidades, key=lambda f: -f["probabilidad_ganador"])

    ratings = rating_service.calcular_ratings()
    distancia_rating = (ratings[0]["rating"] - ratings[-1]["rating"]) if len(ratings) >= 2 else None

    resultado = {
        **info_proximo,
        "fecha_ultimo_torneo": fecha_ultimo.isoformat() if fecha_ultimo else None,
        "dias_desde_ultimo_torneo": dias_desde_ultimo,
        "total_torneos": len(torneos),
        "total_partidos": len(partidos),
        "cantidad_por_modo": cantidad_por_modo,
        "promedio_jugadores_por_torneo": round(promedio_jugadores, 1) if promedio_jugadores else None,
        "top_torneos_mas_jugadores": top_torneos_mas_jugadores,
        "top_torneos_mas_partidos": top_torneos_mas_partidos,
        "top_rivalidades_mas_frecuentes": top_rivalidades_mas_frecuentes,
        "top_rivalidades_mas_parejas": top_rivalidades_mas_parejas,
        "top_padreadas": top_padreadas,
        "top_apariciones_podio": top_apariciones_podio,
        "top_resultados_sorpresivos": top_resultados_sorpresivos,
        "distancia_rating_primero_ultimo": distancia_rating,
    }
    campos_lista = (
        "top_torneos_mas_jugadores", "top_torneos_mas_partidos", "top_rivalidades_mas_frecuentes",
        "top_rivalidades_mas_parejas", "top_padreadas", "top_apariciones_podio", "top_resultados_sorpresivos",
    )
    return estadisticas_config_service.filtrar_visibles(resultado, "generales", campos_lista=campos_lista)
