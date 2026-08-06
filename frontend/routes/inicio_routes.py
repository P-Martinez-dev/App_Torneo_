from flask import Blueprint, render_template, request, redirect, url_for
from services import torneo_service
from auth import requiere_admin

inicio_bp = Blueprint("inicio", __name__)


@inicio_bp.route("/")
def inicio():
    en_curso = torneo_service.torneo_en_curso()
    generales = torneo_service.obtener_estadisticas_generales()
    return render_template("inicio.html", torneo_en_curso=en_curso, generales=generales)


@inicio_bp.route("/descripcion", methods=["POST"])
@requiere_admin
def actualizar_descripcion():
    torneo_service.actualizar_descripcion_inicio(request.form.get("descripcion") or None)
    return redirect(url_for("inicio.inicio"))
