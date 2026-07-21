from flask import Blueprint, request, jsonify
from services import jugador_service

jugador_bp = Blueprint("jugador", __name__, url_prefix="/jugadores")


@jugador_bp.route("", methods=["GET"])
def listar():
    return jsonify(jugador_service.listar_jugadores()), 200


@jugador_bp.route("/<int:jugador_id>", methods=["GET"])
def obtener(jugador_id):
    try:
        return jsonify(jugador_service.obtener_jugador(jugador_id)), 200
    except jugador_service.JugadorNoEncontradoError as e:
        return jsonify({"error": str(e)}), 404


@jugador_bp.route("", methods=["POST"])
def crear():
    datos = request.get_json()
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
    datos = request.get_json()
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