from flask import Blueprint, request, jsonify, send_file
from services import cache_resultados, torneo_service, partido_service, tabla_service, tabla_general_service, torneo_estadisticas_service, estadisticas_generales_service, exportar_service
from repositories import grupo_repository
from controllers.utils import obtener_json_body

torneo_bp = Blueprint("torneo", __name__, url_prefix="/torneos")


# =========================================================
# Creación / consulta de torneo
# =========================================================

@torneo_bp.route("/descripcion-inicio", methods=["PUT"])
def actualizar_descripcion_inicio():
    datos, error = obtener_json_body()
    if error:
        return error
    estadisticas_generales_service.actualizar_descripcion_inicio(datos.get("descripcion"))
    return jsonify({"ok": True}), 200


@torneo_bp.route("/descripcion-tablas", methods=["PUT"])
def actualizar_descripcion_tablas():
    datos, error = obtener_json_body()
    if error:
        return error
    estadisticas_generales_service.actualizar_descripcion_tablas(datos.get("descripcion"))
    return jsonify({"ok": True}), 200


@torneo_bp.route("/infos", methods=["GET"])
def obtener_infos():
    return jsonify(estadisticas_generales_service.obtener_infos()), 200


@torneo_bp.route("/infos/<string:cual>", methods=["PUT"])
def actualizar_info(cual):
    datos, error = obtener_json_body()
    if error:
        return error
    if cual == "tablas":
        estadisticas_generales_service.actualizar_info_tablas(datos.get("texto"))
    elif cual == "formatos":
        estadisticas_generales_service.actualizar_info_formatos(datos.get("texto"))
    else:
        return jsonify({"error": f"'{cual}' no es una info conocida"}), 400
    return jsonify({"ok": True}), 200


@torneo_bp.route("/nombre-club", methods=["GET"])
def obtener_nombre_club():
    return jsonify({"nombre_club": estadisticas_generales_service.obtener_nombre_club()}), 200


@torneo_bp.route("/nombre-club", methods=["PUT"])
def actualizar_nombre_club():
    datos, error = obtener_json_body()
    if error:
        return error
    estadisticas_generales_service.actualizar_nombre_club(datos.get("nombre"))
    return jsonify({"ok": True}), 200


@torneo_bp.route("/tiles/<string:nombre_tile>", methods=["PUT"])
def actualizar_tile(nombre_tile):
    datos, error = obtener_json_body()
    if error:
        return error
    try:
        estadisticas_generales_service.actualizar_tile(nombre_tile, bool(datos.get("visible")))
        return jsonify({"ok": True}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@torneo_bp.route("/proximo-torneo", methods=["PUT"])
def actualizar_proximo_torneo():
    datos, error = obtener_json_body()
    if error:
        return error
    estadisticas_generales_service.actualizar_proximo_torneo(datos.get("fecha"))
    return jsonify({"ok": True}), 200


@torneo_bp.route("/config-general", methods=["GET"])
def config_general():
    return jsonify(cache_resultados.obtener(
        "config-general", estadisticas_generales_service.obtener_config_general
    )), 200


@torneo_bp.route("/estadisticas-generales", methods=["GET"])
def estadisticas_generales():
    return jsonify(cache_resultados.obtener(
        "estadisticas-generales", estadisticas_generales_service.obtener_estadisticas_generales
    )), 200


@torneo_bp.route("", methods=["GET"])
def listar():
    return jsonify(cache_resultados.obtener("listado-torneos", torneo_service.listar_torneos)), 200


@torneo_bp.route("", methods=["POST"])
def crear():
    datos, error = obtener_json_body()
    if error:
        return error
    try:
        nuevo = torneo_service.crear_torneo(
            nombre=datos.get("nombre"),
            modo=datos.get("modo"),
            fecha=datos.get("fecha"),
            jugadores_ids=datos.get("jugadores_ids", []),
            cupos_eliminacion=datos.get("cupos_eliminacion"),
            cantidad_grupos=datos.get("cantidad_grupos"),
            vidas_iniciales=datos.get("vidas_iniciales"),
            orden_jugadores_ids=datos.get("orden_jugadores_ids"),
            grupos_manual=datos.get("grupos_manual"),
            descripcion=datos.get("descripcion"),
        )
        return jsonify(nuevo), 201
    except torneo_service.DatosTorneoInvalidosError as e:
        return jsonify({"error": str(e)}), 400


@torneo_bp.route("/<int:torneo_id>", methods=["GET"])
def obtener(torneo_id):
    try:
        return jsonify(torneo_service.obtener_torneo(torneo_id)), 200
    except torneo_service.TorneoNoEncontradoError as e:
        return jsonify({"error": str(e)}), 404


@torneo_bp.route("/<int:torneo_id>/estadisticas", methods=["GET"])
def estadisticas(torneo_id):
    try:
        return jsonify(torneo_estadisticas_service.obtener_estadisticas_torneo(torneo_id)), 200
    except torneo_estadisticas_service.TorneoNoEncontradoError as e:
        return jsonify({"error": str(e)}), 404


@torneo_bp.route("/<int:torneo_id>/exportar-imagen", methods=["GET"])
def exportar_imagen(torneo_id):
    try:
        buffer = exportar_service.generar_imagen_resumen(torneo_id)
        return send_file(buffer, mimetype="image/png", download_name=f"torneo_{torneo_id}.png")
    except torneo_service.TorneoNoEncontradoError as e:
        return jsonify({"error": str(e)}), 404


@torneo_bp.route("/<int:torneo_id>/navegacion", methods=["GET"])
def navegacion(torneo_id):
    return jsonify(torneo_service.obtener_navegacion(torneo_id)), 200


@torneo_bp.route("/<int:torneo_id>/resumen", methods=["GET"])
def resumen(torneo_id):
    """Todo el desarrollo del torneo en un solo llamado: tablas de cada
    grupo/mini-grupo, bracket de eliminación armado por ronda, y podio si
    ya terminó. Pensado para pintar la pantalla de 'cómo se desarrolló'."""
    try:
        return jsonify(torneo_service.obtener_resumen(torneo_id)), 200
    except torneo_service.TorneoNoEncontradoError as e:
        return jsonify({"error": str(e)}), 404


@torneo_bp.route("/<int:torneo_id>", methods=["PUT"])
def actualizar(torneo_id):
    datos, error = obtener_json_body()
    if error:
        return error
    try:
        actualizado = torneo_service.actualizar_torneo(
            torneo_id, datos.get("nombre"), datos.get("fecha"), datos.get("descripcion")
        )
        return jsonify(actualizado), 200
    except torneo_service.TorneoNoEncontradoError as e:
        return jsonify({"error": str(e)}), 404
    except torneo_service.DatosTorneoInvalidosError as e:
        return jsonify({"error": str(e)}), 400


@torneo_bp.route("/<int:torneo_id>", methods=["DELETE"])
def eliminar(torneo_id):
    try:
        torneo_service.eliminar_torneo(torneo_id)
        return "", 204
    except torneo_service.TorneoNoEncontradoError as e:
        return jsonify({"error": str(e)}), 404


# =========================================================
# Tablas de posiciones (dinámicas, permiten excluir partidos/fechas)
# =========================================================

@torneo_bp.route("/<int:torneo_id>/grupos", methods=["GET"])
def listar_grupos(torneo_id):
    grupos = grupo_repository.obtener_por_torneo(torneo_id)
    return jsonify([g.to_dict() for g in grupos]), 200


@torneo_bp.route("/<int:torneo_id>/tabla", methods=["GET"])
def tabla_todos_contra_todos(torneo_id):
    """Modo 'todos_contra_todos'. Query param opcional: ?excluir=3&excluir=7"""
    excluidos = request.args.getlist("excluir", type=int)
    tabla = tabla_service.calcular_tabla_todos_contra_todos(torneo_id, excluidos)
    return jsonify(tabla), 200


@torneo_bp.route("/<int:torneo_id>/grupos/<int:grupo_id>/tabla", methods=["GET"])
def tabla_grupo(torneo_id, grupo_id):
    """Modo 'grupos_eliminacion'. Query param opcional: ?excluir=3&excluir=7"""
    excluidos = request.args.getlist("excluir", type=int)
    tabla = tabla_service.calcular_tabla_grupo(grupo_id, excluidos)
    return jsonify(tabla), 200


@torneo_bp.route("/<int:torneo_id>/grupos/<int:grupo_id>/contexto-repechaje", methods=["GET"])
def contexto_repechaje(torneo_id, grupo_id):
    """Resumen justificativo para la pantalla de forzado de clasificados."""
    return jsonify(tabla_service.contexto_repechaje(torneo_id, grupo_id)), 200


@torneo_bp.route("/tabla-general/exportar-imagen", methods=["GET"])
def exportar_imagen_tabla_general():
    excluidos_ids = request.args.getlist("excluir", type=int)
    buffer = exportar_service.generar_imagen_tabla_general(excluidos_ids)
    return send_file(buffer, mimetype="image/png", download_name="ranking_general.png")


@torneo_bp.route("/tabla-general", methods=["GET"])
def tabla_general():
    """Ranking histórico de campeonatos. Query param opcional: ?excluir=4&excluir=7"""
    torneos_excluidos = request.args.getlist("excluir", type=int)
    # La clave incluye los excluidos: filtrar cambia el ranking, así que
    # cada combinación de filtros se cachea por separado.
    clave = f"tabla-general:{sorted(torneos_excluidos)}"
    tabla = cache_resultados.obtener(
        clave, lambda: tabla_general_service.calcular_tabla_general(torneos_excluidos)
    )
    return jsonify(tabla), 200


# =========================================================
# Clasificación (empates sin resolver -> reintentar o forzar)
# =========================================================

# =========================================================
# Bracket de eliminación (grupos_eliminacion): resembrado manual, para
# reconstruir torneos que ya se jugaron en la vida real
# =========================================================

@torneo_bp.route("/<int:torneo_id>/bracket", methods=["GET"])
def obtener_bracket(torneo_id):
    return jsonify(partido_service.obtener_bracket_ronda1(torneo_id)), 200


@torneo_bp.route("/<int:torneo_id>/bracket", methods=["PUT"])
def resembrar_bracket(torneo_id):
    datos, error = obtener_json_body()
    if error:
        return error
    try:
        partido_service.resembrar_bracket_manual(torneo_id, datos.get("emparejamientos", []))
        return jsonify(partido_service.obtener_bracket_ronda1(torneo_id)), 200
    except partido_service.BracketInvalidoError as e:
        return jsonify({"error": str(e)}), 400


# =========================================================
# Clasificación (empates sin resolver -> reintentar o forzar)
# =========================================================

@torneo_bp.route("/<int:torneo_id>/reintentar-desempate", methods=["POST"])
def reintentar_desempate(torneo_id):
    datos, error = obtener_json_body()
    if error:
        return error
    try:
        grupo_id = partido_service.reintentar_desempate(
            torneo_id,
            datos.get("grupo_id"),
            datos.get("jugadores_empatados_ids", []),
            datos.get("slots"),
        )
        return jsonify({"grupo_id": grupo_id}), 201
    except partido_service.ClasificacionInvalidaError as e:
        return jsonify({"error": str(e)}), 400


@torneo_bp.route("/<int:torneo_id>/forzar-clasificado", methods=["POST"])
def forzar_clasificado(torneo_id):
    datos, error = obtener_json_body()
    if error:
        return error
    try:
        partido_service.forzar_clasificado(
            torneo_id,
            jugador_id=datos.get("jugador_id"),
            clasificado=datos.get("clasificado"),
            observacion=datos.get("observacion"),
        )
        return "", 204
    except partido_service.ClasificacionInvalidaError as e:
        return jsonify({"error": str(e)}), 400

@torneo_bp.route("/warmup/progreso", methods=["GET"])
def warmup_progreso():
    """Estado del warmup del cache -- para la pantalla de 'cargando'
    del frontend. No devuelve ningún dato del negocio, solo progreso."""
    return jsonify(cache_resultados.estado_warmup()), 200
