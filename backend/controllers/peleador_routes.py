from flask import Blueprint, request, jsonify
from services import peleador_service

peleador_bp = Blueprint("peleador", __name__, url_prefix="/peleadores")


@peleador_bp.route("", methods=["GET"])
def listar():
    return jsonify(peleador_service.listar_peleadores()), 200


@peleador_bp.route("/<int:peleador_id>", methods=["GET"])
def obtener(peleador_id):
    try:
        return jsonify(peleador_service.obtener_peleador(peleador_id)), 200
    except peleador_service.PeleadorNoEncontradoError as e:
        return jsonify({"error": str(e)}), 404


@peleador_bp.route("", methods=["POST"])
def crear():
    datos = request.get_json()
    try:
        nuevo = peleador_service.crear_peleador(nombre=datos.get("nombre"))
        return jsonify(nuevo), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@peleador_bp.route("/<int:peleador_id>", methods=["PUT"])
def actualizar(peleador_id):
    datos = request.get_json()
    try:
        actualizado = peleador_service.actualizar_peleador(peleador_id, nombre=datos.get("nombre"))
        return jsonify(actualizado), 200
    except peleador_service.PeleadorNoEncontradoError as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@peleador_bp.route("/<int:peleador_id>", methods=["DELETE"])
def eliminar(peleador_id):
    try:
        peleador_service.eliminar_peleador(peleador_id)
        return "", 204
    except peleador_service.PeleadorNoEncontradoError as e:
        return jsonify({"error": str(e)}), 404
    except peleador_service.PeleadorConHistorialError as e:
        return jsonify({"error": str(e)}), 409