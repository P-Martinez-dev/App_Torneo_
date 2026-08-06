from datetime import datetime
from flask import Blueprint, jsonify, send_file
from services import admin_service, estadisticas_config_service, backup_service
from controllers.utils import obtener_json_body

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/backup", methods=["GET"])
def backup():
    buffer = backup_service.generar_backup_completo()
    nombre = f"backup_{datetime.now().strftime('%Y%m%d_%H%M')}.zip"
    return send_file(buffer, mimetype="application/zip", download_name=nombre, as_attachment=True)


@admin_bp.route("/estadisticas-config", methods=["GET"])
def estadisticas_config():
    return jsonify(estadisticas_config_service.obtener_registro_con_estado()), 200


@admin_bp.route("/estadisticas-config", methods=["PUT"])
def actualizar_estadisticas_config():
    datos, error = obtener_json_body()
    if error:
        return error
    try:
        estadisticas_config_service.actualizar_visibilidad(datos.get("clave"), bool(datos.get("visible")))
        return jsonify({"ok": True}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@admin_bp.route("/login", methods=["POST"])
def login():
    datos, error = obtener_json_body()
    if error:
        return error
    try:
        admin = admin_service.verificar_credenciales(datos.get("usuario"), datos.get("password"))
        return jsonify(admin), 200
    except admin_service.CredencialesInvalidasError as e:
        return jsonify({"error": str(e)}), 401


@admin_bp.route("", methods=["GET"])
def listar():
    return jsonify(admin_service.listar_admins()), 200


@admin_bp.route("", methods=["POST"])
def crear():
    datos, error = obtener_json_body()
    if error:
        return error
    try:
        nuevo = admin_service.crear_admin(datos.get("usuario"), datos.get("password"))
        return jsonify(nuevo), 201
    except admin_service.UsuarioYaExisteError as e:
        return jsonify({"error": str(e)}), 409
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@admin_bp.route("/<int:admin_id>", methods=["DELETE"])
def eliminar(admin_id):
    try:
        admin_service.eliminar_admin(admin_id)
        return "", 204
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
