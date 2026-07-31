from flask import Blueprint, render_template, request, redirect, url_for, flash
from services import peleador_service

configuracion_bp = Blueprint("configuracion", __name__, url_prefix="/configuracion")


@configuracion_bp.route("")
def index():
    return render_template("configuracion/index.html")


@configuracion_bp.route("/peleadores")
def peleadores():
    lista = peleador_service.listar_peleadores()
    return render_template("configuracion/peleadores.html", peleadores=lista)


@configuracion_bp.route("/peleadores/crear", methods=["POST"])
def crear_peleador():
    try:
        peleador_service.crear_peleador(request.form.get("nombre"))
    except peleador_service.PeleadorInvalidoError as e:
        flash(str(e))
    return redirect(url_for("configuracion.peleadores"))


@configuracion_bp.route("/peleadores/<int:peleador_id>/editar", methods=["POST"])
def editar_peleador(peleador_id):
    try:
        peleador_service.actualizar_peleador(peleador_id, request.form.get("nombre"))
    except peleador_service.PeleadorInvalidoError as e:
        flash(str(e))
    return redirect(url_for("configuracion.peleadores"))


@configuracion_bp.route("/peleadores/<int:peleador_id>/eliminar", methods=["POST"])
def eliminar_peleador(peleador_id):
    try:
        peleador_service.eliminar_peleador(peleador_id)
    except peleador_service.PeleadorConHistorialError as e:
        flash(str(e))
    return redirect(url_for("configuracion.peleadores"))
