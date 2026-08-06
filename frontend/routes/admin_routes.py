from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from services import admin_service
from auth import requiere_admin, es_admin

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if es_admin():
        return redirect(url_for("inicio.inicio"))

    if request.method == "GET":
        return render_template("admin/login.html", error=None)

    try:
        admin = admin_service.verificar_credenciales(request.form.get("usuario"), request.form.get("password"))
        session["admin_usuario"] = admin["usuario"]
        siguiente = request.args.get("siguiente")
        return redirect(siguiente or url_for("inicio.inicio"))
    except admin_service.CredencialesInvalidasError as e:
        return render_template("admin/login.html", error=str(e))


@admin_bp.route("/logout", methods=["POST"])
def logout():
    session.pop("admin_usuario", None)
    flash("Sesión cerrada.")
    return redirect(url_for("inicio.inicio"))


@admin_bp.route("/usuarios")
@requiere_admin
def usuarios():
    admins = admin_service.listar_admins()
    return render_template("admin/usuarios.html", admins=admins)


@admin_bp.route("/usuarios/crear", methods=["POST"])
@requiere_admin
def crear():
    try:
        admin_service.crear_admin(request.form.get("usuario"), request.form.get("password"))
        flash("Admin creado.")
    except admin_service.AdminInvalidoError as e:
        flash(str(e))
    return redirect(url_for("admin.usuarios"))


@admin_bp.route("/usuarios/<int:admin_id>/eliminar", methods=["POST"])
@requiere_admin
def eliminar(admin_id):
    try:
        admin_service.eliminar_admin(admin_id)
        flash("Admin eliminado.")
    except admin_service.AdminInvalidoError as e:
        flash(str(e))
    return redirect(url_for("admin.usuarios"))


@admin_bp.route("/estadisticas")
@requiere_admin
def estadisticas_config():
    registro = admin_service.obtener_estadisticas_config()
    categorias = {}
    for item in registro:
        categorias.setdefault(item["categoria"], []).append(item)
    return render_template("admin/estadisticas.html", categorias=categorias)


@admin_bp.route("/estadisticas/toggle", methods=["POST"])
@requiere_admin
def toggle_estadistica():
    clave = request.form.get("clave")
    visible = request.form.get("visible") == "true"
    admin_service.actualizar_estadistica_visible(clave, visible)
    return redirect(url_for("admin.estadisticas_config"))
