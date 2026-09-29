from flask import Blueprint, jsonify
from services import cache_resultados, enfrentamiento_service

enfrentamiento_bp = Blueprint("enfrentamiento", __name__, url_prefix="/enfrentamientos")


@enfrentamiento_bp.route("/<int:jugador_a_id>/<int:jugador_b_id>", methods=["GET"])
def obtener(jugador_a_id, jugador_b_id):
    """Cara a cara entre dos jugadores: récord e historial de partidos.
    La clave de cache respeta el orden A-B porque la respuesta viene
    orientada desde A (A-B y B-A son dos respuestas distintas)."""
    try:
        return jsonify(cache_resultados.obtener(
            f"enfrentamiento-{jugador_a_id}-{jugador_b_id}",
            lambda: enfrentamiento_service.obtener_enfrentamiento(jugador_a_id, jugador_b_id)
        )), 200
    except enfrentamiento_service.EnfrentamientoInvalidoError as e:
        return jsonify({"error": str(e)}), 400
    except enfrentamiento_service.JugadorNoEncontradoError as e:
        return jsonify({"error": str(e)}), 404
