from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from services import torneo_service
from auth import requiere_admin

inicio_bp = Blueprint("inicio", __name__)


@inicio_bp.route("/estado-carga")
def estado_carga():
    """Progreso del precalentado, para la pantalla de carga. El navegador
    le pregunta a ESTA ruta (mismo origen) y no al backend directo: así la
    clave interna nunca sale del servidor."""
    try:
        return jsonify(torneo_service.estado_warmup())
    except Exception:
        # Si el backend no responde, decimos que ya está listo para no
        # dejar a nadie trabado en la pantalla de carga -- que entre y
        # vea el error real, si lo hay.
        return jsonify({"completado": True, "pasos_hechos": 0, "pasos_totales": 0, "paso_actual": None})


@inicio_bp.route("/")
def inicio():
    en_curso = torneo_service.torneo_en_curso()
    generales = torneo_service.obtener_config_general()
    return render_template("inicio.html", torneo_en_curso=en_curso, generales=generales)


@inicio_bp.route("/descripcion", methods=["POST"])
@requiere_admin
def actualizar_descripcion():
    torneo_service.actualizar_descripcion_inicio(request.form.get("descripcion") or None)
    return redirect(url_for("inicio.inicio"))
