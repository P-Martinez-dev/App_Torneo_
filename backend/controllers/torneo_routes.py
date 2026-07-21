from flask import Blueprint, request, jsonify
from services import torneo_service, partido_service, tabla_service

torneo_bp = Blueprint("torneo", __name__, url_prefix="/torneos")


# =========================================================
# Creación / consulta de torneo
# =========================================================

@torneo_bp.route("", methods=["POST"])
def crear():
    datos = request.get_json()
    try:
        nuevo = torneo_service.crear_torneo(
            nombre=datos.get("nombre"),
            modo=datos.get("modo"),
            fecha=datos.get("fecha"),
            jugadores_ids=datos.get("jugadores_ids", []),
            cupos_eliminacion=datos.get("cupos_eliminacion"),
            cantidad_grupos=datos.get("cantidad_grupos"),
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


# =========================================================
# Tablas de posiciones (dinámicas, permiten excluir partidos/fechas)
# =========================================================

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


# =========================================================
# Clasificación (empates sin resolver -> reintentar o forzar)
# =========================================================

@torneo_bp.route("/<int:torneo_id>/reintentar-desempate", methods=["POST"])
def reintentar_desempate(torneo_id):
    datos = request.get_json()
    grupo_id = partido_service.reintentar_desempate(
        torneo_id,
        datos.get("jugadores_empatados_ids", []),
        datos.get("slots"),
    )
    return jsonify({"grupo_id": grupo_id}), 201


@torneo_bp.route("/<int:torneo_id>/forzar-clasificado", methods=["POST"])
def forzar_clasificado(torneo_id):
    datos = request.get_json()
    partido_service.forzar_clasificado(
        torneo_id,
        jugador_id=datos.get("jugador_id"),
        clasificado=datos.get("clasificado"),
        observacion=datos.get("observacion"),
    )
    return "", 204