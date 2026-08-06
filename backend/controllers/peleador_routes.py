from flask import Blueprint, request, jsonify
from services import peleador_service, estadisticas_peleador_service
from controllers.utils import obtener_json_body

peleador_bp = Blueprint("peleador", __name__, url_prefix="/peleadores")


@peleador_bp.route("/<int:peleador_id>/estadisticas", methods=["GET"])
def estadisticas(peleador_id):
    return jsonify(estadisticas_peleador_service.obtener_estadisticas_peleador(peleador_id)), 200


@peleador_bp.route("/<int:peleador_id>/navegacion", methods=["GET"])
def navegacion(peleador_id):
    return jsonify(peleador_service.obtener_navegacion(peleador_id)), 200


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
    datos, error = obtener_json_body()
    if error:
        return error
    try:
        nuevo = peleador_service.crear_peleador(nombre=datos.get("nombre"))
        return jsonify(nuevo), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@peleador_bp.route("/<int:peleador_id>", methods=["PUT"])
def actualizar(peleador_id):
    datos, error = obtener_json_body()
    if error:
        return error
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


@peleador_bp.route("/<int:peleador_id>/icono", methods=["POST"])
def subir_icono(peleador_id):
    archivo = request.files.get("imagen")
    try:
        actualizado = peleador_service.subir_icono(peleador_id, archivo)
        return jsonify(actualizado), 200
    except peleador_service.PeleadorNoEncontradoError as e:
        return jsonify({"error": str(e)}), 404
    except peleador_service.ImagenInvalidaError as e:
        return jsonify({"error": str(e)}), 400


@peleador_bp.route("/<int:peleador_id>/icono", methods=["DELETE"])
def eliminar_icono(peleador_id):
    try:
        actualizado = peleador_service.eliminar_icono(peleador_id)
        return jsonify(actualizado), 200
    except peleador_service.PeleadorNoEncontradoError as e:
        return jsonify({"error": str(e)}), 404


@peleador_bp.route("/limpiar-imagenes-rotas", methods=["POST"])
def limpiar_imagenes_rotas():
    limpiadas = peleador_service.limpiar_imagenes_rotas()
    return jsonify({"limpiadas": limpiadas}), 200