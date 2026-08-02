from flask import Blueprint, render_template, request, redirect, url_for
from services import torneo_service, jugador_service

torneo_bp = Blueprint("torneo", __name__, url_prefix="/torneos")


@torneo_bp.route("")
def listado():
    torneos = torneo_service.listar_torneos()
    excluidos_ids = request.args.getlist("excluir", type=int)
    tabla = torneo_service.tabla_general(excluidos_ids)
    return render_template(
        "torneos/listado.html", torneos=torneos, tabla_general=tabla, excluidos_ids=excluidos_ids
    )


@torneo_bp.route("/<int:torneo_id>")
def detalle(torneo_id):
    resumen = torneo_service.obtener_resumen(torneo_id)
    return render_template("torneos/detalle.html", torneo_id=torneo_id, resumen=resumen)


@torneo_bp.route("/<int:torneo_id>/eliminar", methods=["POST"])
def eliminar(torneo_id):
    """Se usa desde el diálogo de 'descartar el torneo en desarrollo' en Inicio."""
    torneo_service.eliminar_torneo(torneo_id)
    return redirect(url_for("torneo.crear"))


@torneo_bp.route("/nuevo", methods=["GET", "POST"])
def crear():
    if request.method == "GET":
        jugadores = jugador_service.listar_jugadores()
        return render_template("torneos/crear.html", jugadores=jugadores, error=None, form=None)

    payload = torneo_service.armar_payload_creacion(request.form)
    try:
        nuevo = torneo_service.crear_torneo(payload)
        return redirect(url_for("partido.actual", torneo_id=nuevo["id"]))
    except torneo_service.TorneoInvalidoError as e:
        jugadores = jugador_service.listar_jugadores()
        return render_template(
            "torneos/crear.html", jugadores=jugadores, error=str(e), form=request.form
        ), 400
