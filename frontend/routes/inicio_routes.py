from flask import Blueprint, render_template
from services import torneo_service

inicio_bp = Blueprint("inicio", __name__)


@inicio_bp.route("/")
def inicio():
    en_curso = torneo_service.torneo_en_curso()
    return render_template("inicio.html", torneo_en_curso=en_curso)
