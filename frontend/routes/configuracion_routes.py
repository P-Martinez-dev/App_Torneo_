from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from services import peleador_service, jugador_service, torneo_service, admin_service
from auth import requiere_admin

configuracion_bp = Blueprint("configuracion", __name__, url_prefix="/configuracion")


@configuracion_bp.route("")
@requiere_admin
def index():
    generales = torneo_service.obtener_config_general()
    return render_template("configuracion/index.html", generales=generales)


@configuracion_bp.route("/proximo-torneo", methods=["POST"])
@requiere_admin
def actualizar_proximo_torneo():
    fecha = request.form.get("fecha") or None
    torneo_service.actualizar_proximo_torneo(fecha)
    flash("Próximo torneo actualizado." if fecha else "Se borró la fecha del próximo torneo.")
    return redirect(url_for("configuracion.index"))


@configuracion_bp.route("/nombre-club", methods=["POST"])
@requiere_admin
def actualizar_nombre_club():
    torneo_service.actualizar_nombre_club(request.form.get("nombre"))
    flash("Nombre actualizado.")
    return redirect(url_for("configuracion.index"))


@configuracion_bp.route("/tiles/<string:nombre_tile>/toggle", methods=["POST"])
@requiere_admin
def toggle_tile(nombre_tile):
    visible = request.form.get("visible") == "true"
    torneo_service.actualizar_tile(nombre_tile, visible)
    return redirect(url_for("configuracion.index"))


@configuracion_bp.route("/backup")
@requiere_admin
def backup():
    contenido = admin_service.descargar_backup()
    return Response(contenido, mimetype="application/zip", headers={
        "Content-Disposition": 'attachment; filename="backup.zip"'
    })


@configuracion_bp.route("/limpiar-imagenes-rotas", methods=["POST"])
@requiere_admin
def limpiar_imagenes_rotas():
    limpiadas = jugador_service.limpiar_imagenes_rotas() + peleador_service.limpiar_imagenes_rotas()
    if limpiadas:
        flash(f"Se limpiaron {limpiadas} referencia(s) a imágenes que ya no existían en disco.")
    else:
        flash("No había ninguna referencia rota -- todo en orden.")
    return redirect(url_for("configuracion.index"))
