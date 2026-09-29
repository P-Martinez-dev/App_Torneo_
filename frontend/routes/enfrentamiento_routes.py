from flask import Blueprint, render_template, redirect, url_for, flash
from services import enfrentamiento_service, jugador_service

enfrentamiento_bp = Blueprint("enfrentamiento", __name__, url_prefix="/enfrentamientos")


@enfrentamiento_bp.route("")
def selector():
    jugadores = jugador_service.listar_jugadores()
    return render_template("enfrentamientos/selector.html", jugadores=jugadores)


@enfrentamiento_bp.route("/<int:jugador_a_id>/<int:jugador_b_id>")
def detalle(jugador_a_id, jugador_b_id):
    try:
        enfrentamiento = enfrentamiento_service.obtener_enfrentamiento(jugador_a_id, jugador_b_id)
    except enfrentamiento_service.EnfrentamientoInvalidoError as e:
        flash(str(e))
        return redirect(url_for("enfrentamiento.selector"))
    if enfrentamiento is None:
        flash("Alguno de esos jugadores no existe.")
        return redirect(url_for("enfrentamiento.selector"))
    return render_template("enfrentamientos/detalle.html", enfrentamiento=enfrentamiento)
