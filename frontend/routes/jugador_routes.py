from flask import Blueprint, render_template, request, redirect, url_for, flash
from services import jugador_service, estadisticas_service

jugador_bp = Blueprint("jugador", __name__, url_prefix="/jugadores")


@jugador_bp.route("")
def grid():
    jugadores = jugador_service.listar_jugadores()
    return render_template("jugadores/listado.html", jugadores=jugadores)


@jugador_bp.route("/nuevo", methods=["GET", "POST"])
def crear():
    if request.method == "GET":
        return render_template("jugadores/crear.html", error=None, form=None)

    try:
        nuevo = jugador_service.crear_jugador(
            nombre=request.form.get("nombre"),
            fecha_nacimiento=request.form.get("fecha_nacimiento"),
        )
        return redirect(url_for("jugador.detalle", jugador_id=nuevo["id"]))
    except jugador_service.JugadorInvalidoError as e:
        return render_template("jugadores/crear.html", error=str(e), form=request.form), 400


@jugador_bp.route("/<int:jugador_id>")
def detalle(jugador_id):
    jugador = jugador_service.obtener_jugador(jugador_id)
    if jugador is None:
        flash("Ese jugador no existe.")
        return redirect(url_for("jugador.grid"))
    estadisticas = estadisticas_service.obtener_estadisticas(jugador_id)
    return render_template("jugadores/detalle.html", jugador=jugador, estadisticas=estadisticas)


@jugador_bp.route("/<int:jugador_id>/editar", methods=["GET", "POST"])
def editar(jugador_id):
    jugador = jugador_service.obtener_jugador(jugador_id)
    if jugador is None:
        flash("Ese jugador no existe.")
        return redirect(url_for("jugador.grid"))

    if request.method == "GET":
        return render_template("jugadores/editar.html", jugador=jugador, error=None)

    try:
        jugador_service.actualizar_jugador(
            jugador_id,
            nombre=request.form.get("nombre"),
            fecha_nacimiento=request.form.get("fecha_nacimiento"),
        )
        return redirect(url_for("jugador.detalle", jugador_id=jugador_id))
    except jugador_service.JugadorInvalidoError as e:
        return render_template("jugadores/editar.html", jugador=jugador, error=str(e)), 400


@jugador_bp.route("/<int:jugador_id>/eliminar", methods=["POST"])
def eliminar(jugador_id):
    try:
        jugador_service.eliminar_jugador(jugador_id)
        return redirect(url_for("jugador.grid"))
    except jugador_service.JugadorConHistorialError as e:
        flash(str(e))
        return redirect(url_for("jugador.editar", jugador_id=jugador_id))


@jugador_bp.route("/<int:jugador_id>/imagen-vertical", methods=["POST"])
def subir_imagen_vertical(jugador_id):
    archivo = request.files.get("imagen")
    try:
        if archivo and archivo.filename:
            jugador_service.subir_imagen_vertical(jugador_id, archivo)
    except jugador_service.ImagenInvalidaError as e:
        flash(str(e))
    return redirect(url_for("jugador.editar", jugador_id=jugador_id))


@jugador_bp.route("/<int:jugador_id>/imagen-vertical/eliminar", methods=["POST"])
def eliminar_imagen_vertical(jugador_id):
    jugador_service.eliminar_imagen_vertical(jugador_id)
    return redirect(url_for("jugador.editar", jugador_id=jugador_id))


@jugador_bp.route("/<int:jugador_id>/icono", methods=["POST"])
def subir_icono(jugador_id):
    archivo = request.files.get("imagen")
    try:
        if archivo and archivo.filename:
            jugador_service.subir_icono(jugador_id, archivo)
    except jugador_service.ImagenInvalidaError as e:
        flash(str(e))
    return redirect(url_for("jugador.editar", jugador_id=jugador_id))


@jugador_bp.route("/<int:jugador_id>/icono/eliminar", methods=["POST"])
def eliminar_icono(jugador_id):
    jugador_service.eliminar_icono(jugador_id)
    return redirect(url_for("jugador.editar", jugador_id=jugador_id))
