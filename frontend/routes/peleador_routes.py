from flask import Blueprint, render_template, request, redirect, url_for, flash
from services import peleador_service
from auth import requiere_admin

peleador_frontend_bp = Blueprint("peleador_frontend", __name__, url_prefix="/peleadores")


@peleador_frontend_bp.route("")
def listado():
    lista = peleador_service.listar_peleadores()
    return render_template("peleadores/listado.html", peleadores=lista)


@peleador_frontend_bp.route("/<int:peleador_id>")
def detalle(peleador_id):
    peleador = peleador_service.obtener_peleador(peleador_id)
    if peleador is None:
        flash("Ese peleador no existe.")
        return redirect(url_for("peleador_frontend.listado"))
    estadisticas = peleador_service.obtener_estadisticas(peleador_id)
    navegacion = peleador_service.obtener_navegacion(peleador_id)
    return render_template(
        "peleadores/detalle.html", peleador=peleador, estadisticas=estadisticas, navegacion=navegacion
    )


@peleador_frontend_bp.route("/crear", methods=["POST"])
@requiere_admin
def crear():
    try:
        peleador_service.crear_peleador(request.form.get("nombre"))
    except peleador_service.PeleadorInvalidoError as e:
        flash(str(e))
    return redirect(url_for("peleador_frontend.listado"))


@peleador_frontend_bp.route("/<int:peleador_id>/editar", methods=["GET", "POST"])
@requiere_admin
def editar(peleador_id):
    peleador = peleador_service.obtener_peleador(peleador_id)
    if peleador is None:
        flash("Ese peleador no existe.")
        return redirect(url_for("peleador_frontend.listado"))

    if request.method == "GET":
        return render_template("peleadores/editar.html", peleador=peleador, error=None)

    try:
        peleador_service.actualizar_peleador(peleador_id, request.form.get("nombre"))
        return redirect(url_for("peleador_frontend.detalle", peleador_id=peleador_id))
    except peleador_service.PeleadorInvalidoError as e:
        return render_template("peleadores/editar.html", peleador=peleador, error=str(e))


@peleador_frontend_bp.route("/<int:peleador_id>/eliminar", methods=["POST"])
@requiere_admin
def eliminar(peleador_id):
    try:
        peleador_service.eliminar_peleador(peleador_id)
    except peleador_service.PeleadorConHistorialError as e:
        flash(str(e))
    return redirect(url_for("peleador_frontend.listado"))


@peleador_frontend_bp.route("/<int:peleador_id>/icono", methods=["POST"])
@requiere_admin
def subir_icono(peleador_id):
    archivo = request.files.get("imagen")
    try:
        if archivo and archivo.filename:
            peleador_service.subir_icono(peleador_id, archivo)
    except peleador_service.ImagenInvalidaError as e:
        flash(str(e))
    return redirect(url_for("peleador_frontend.editar", peleador_id=peleador_id))


@peleador_frontend_bp.route("/<int:peleador_id>/icono/eliminar", methods=["POST"])
@requiere_admin
def eliminar_icono(peleador_id):
    peleador_service.eliminar_icono(peleador_id)
    return redirect(url_for("peleador_frontend.editar", peleador_id=peleador_id))
