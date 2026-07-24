from flask import Blueprint, request, jsonify
from services import partido_service

partido_bp = Blueprint("partido", __name__)


@partido_bp.route("/torneos/<int:torneo_id>/partido-actual", methods=["GET"])
def obtener_partido_actual(torneo_id):
    partido = partido_service.obtener_partido_actual(torneo_id)
    if partido is None:
        return jsonify({"mensaje": "No quedan partidos pendientes en este torneo"}), 404
    return jsonify(partido), 200


@partido_bp.route("/torneos/<int:torneo_id>/partido-actual", methods=["POST"])
def seleccionar_partido_actual(torneo_id):
    """Navegar a otro enfrentamiento. El que estaba en pantalla queda pospuesto."""
    datos = request.get_json()
    partido = partido_service.seleccionar_partido_actual(torneo_id, datos.get("partido_id"))
    return jsonify(partido), 200


@partido_bp.route("/torneos/<int:torneo_id>/partidos-pendientes", methods=["GET"])
def listar_pendientes(torneo_id):
    """Para el selector de 'ver otros enfrentamientos' (pendientes + pospuestos)."""
    return jsonify(partido_service.listar_partidos_pendientes(torneo_id)), 200


@partido_bp.route("/partidos/<int:partido_id>/resultado", methods=["POST"])
def cargar_resultado(partido_id):
    datos = request.get_json()
    try:
        partido = partido_service.cargar_resultado(partido_id, datos.get("ganador_id"))
        return jsonify(partido), 200
    except partido_service.ResultadoInvalidoError as e:
        return jsonify({"error": str(e)}), 400