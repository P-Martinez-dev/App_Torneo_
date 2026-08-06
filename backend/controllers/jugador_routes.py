from flask import Blueprint, request, jsonify
from services import jugador_service, estadisticas_service, rating_service
from controllers.utils import obtener_json_body

jugador_bp = Blueprint("jugador", __name__, url_prefix="/jugadores")


@jugador_bp.route("/rating", methods=["GET"])
def rating():
    return jsonify(rating_service.calcular_ratings()), 200


@jugador_bp.route("/limpiar-imagenes-rotas", methods=["POST"])
def limpiar_imagenes_rotas():
    limpiadas = jugador_service.limpiar_imagenes_rotas()
    return jsonify({"limpiadas": limpiadas}), 200


@jugador_bp.route("", methods=["GET"])
def listar():
    return jsonify(jugador_service.listar_jugadores()), 200


@jugador_bp.route("/<int:jugador_id>/navegacion", methods=["GET"])
def navegacion(jugador_id):
    return jsonify(jugador_service.obtener_navegacion(jugador_id)), 200


@jugador_bp.route("/<int:jugador_id>", methods=["GET"])
def obtener(jugador_id):
    try:
        return jsonify(jugador_service.obtener_jugador(jugador_id)), 200
    except jugador_service.JugadorNoEncontradoError as e:
        return jsonify({"error": str(e)}), 404


@jugador_bp.route("/<int:jugador_id>/estadisticas", methods=["GET"])
def estadisticas(jugador_id):
    """Estadísticas históricas del jugador: rivales, peleadores, rachas,
    mejor puesto y veces campeón, sumando todos sus torneos."""
    try:
        return jsonify(estadisticas_service.obtener_estadisticas_jugador(jugador_id)), 200
    except estadisticas_service.JugadorNoEncontradoError as e:
        return jsonify({"error": str(e)}), 404


@jugador_bp.route("", methods=["POST"])
def crear():
    datos, error = obtener_json_body()
    if error:
        return error
    try:
        nuevo = jugador_service.crear_jugador(
            nombre=datos.get("nombre"),
            fecha_nacimiento=datos.get("fecha_nacimiento"),
        )
        return jsonify(nuevo), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@jugador_bp.route("/<int:jugador_id>", methods=["PUT"])
def actualizar(jugador_id):
    datos, error = obtener_json_body()
    if error:
        return error
    try:
        actualizado = jugador_service.actualizar_jugador(
            jugador_id,
            nombre=datos.get("nombre"),
            fecha_nacimiento=datos.get("fecha_nacimiento"),
        )
        return jsonify(actualizado), 200
    except jugador_service.JugadorNoEncontradoError as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@jugador_bp.route("/<int:jugador_id>", methods=["DELETE"])
def eliminar(jugador_id):
    try:
        jugador_service.eliminar_jugador(jugador_id)
        return "", 204
    except jugador_service.JugadorNoEncontradoError as e:
        return jsonify({"error": str(e)}), 404
    except jugador_service.JugadorConHistorialError as e:
        return jsonify({"error": str(e)}), 409


# =========================================================
# Imágenes (multipart, no JSON -- por eso no pasan por obtener_json_body)
# =========================================================

@jugador_bp.route("/<int:jugador_id>/imagen-vertical", methods=["POST"])
def subir_imagen_vertical(jugador_id):
    try:
        actualizado = jugador_service.subir_imagen_vertical(jugador_id, request.files.get("imagen"))
        return jsonify(actualizado), 200
    except jugador_service.JugadorNoEncontradoError as e:
        return jsonify({"error": str(e)}), 404
    except jugador_service.ImagenInvalidaError as e:
        return jsonify({"error": str(e)}), 400


@jugador_bp.route("/<int:jugador_id>/imagen-vertical", methods=["DELETE"])
def eliminar_imagen_vertical(jugador_id):
    try:
        actualizado = jugador_service.eliminar_imagen_vertical(jugador_id)
        return jsonify(actualizado), 200
    except jugador_service.JugadorNoEncontradoError as e:
        return jsonify({"error": str(e)}), 404


@jugador_bp.route("/<int:jugador_id>/icono", methods=["POST"])
def subir_icono(jugador_id):
    try:
        actualizado = jugador_service.subir_icono(jugador_id, request.files.get("imagen"))
        return jsonify(actualizado), 200
    except jugador_service.JugadorNoEncontradoError as e:
        return jsonify({"error": str(e)}), 404
    except jugador_service.ImagenInvalidaError as e:
        return jsonify({"error": str(e)}), 400


@jugador_bp.route("/<int:jugador_id>/icono", methods=["DELETE"])
def eliminar_icono(jugador_id):
    try:
        actualizado = jugador_service.eliminar_icono(jugador_id)
        return jsonify(actualizado), 200
    except jugador_service.JugadorNoEncontradoError as e:
        return jsonify({"error": str(e)}), 404