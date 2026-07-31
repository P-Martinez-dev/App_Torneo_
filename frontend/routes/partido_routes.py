from flask import Blueprint, render_template, request, redirect, url_for, flash
from services import partido_service, jugador_service, peleador_service

partido_bp = Blueprint("partido", __name__, url_prefix="/torneos/<int:torneo_id>/partido-actual")


def _nombres_jugadores():
    return {j["id"]: j["nombre"] for j in jugador_service.listar_jugadores()}


@partido_bp.route("")
def actual(torneo_id):
    estado = partido_service.obtener_estado_actual(torneo_id)
    nombres = _nombres_jugadores()

    if estado["tipo"] == "partido":
        partido = estado["partido"]
        return render_template(
            "partidos/actual.html", torneo_id=torneo_id, partido=partido,
            nombre1=nombres.get(partido["jugador1_id"]), nombre2=nombres.get(partido["jugador2_id"]),
            peleadores=peleador_service.listar_peleadores(),
        )

    if estado["tipo"] == "empate_sin_resolver":
        empatados = [{"id": jid, "nombre": nombres.get(jid)} for jid in estado["empatados"]]
        return render_template(
            "partidos/decision_critica.html", torneo_id=torneo_id,
            grupo_id=estado["grupo_id"], slots=estado["slots"], empatados=empatados,
        )

    if estado["tipo"] == "finalizado":
        return render_template("partidos/finalizado.html", torneo_id=torneo_id)

    return render_template("partidos/sin_partidos.html", torneo_id=torneo_id)


@partido_bp.route("/pendientes")
def pendientes(torneo_id):
    lista = partido_service.listar_pendientes(torneo_id)
    nombres = _nombres_jugadores()
    for p in lista:
        p["nombre1"] = nombres.get(p["jugador1_id"])
        p["nombre2"] = nombres.get(p["jugador2_id"])
    return render_template("partidos/pendientes.html", torneo_id=torneo_id, pendientes=lista)


@partido_bp.route("/posponer", methods=["POST"])
def posponer(torneo_id):
    partido_id = request.form.get("partido_id", type=int)
    try:
        partido_service.seleccionar_partido(torneo_id, partido_id)
    except partido_service.PartidoInvalidoError as e:
        flash(str(e))
    return redirect(url_for("partido.actual", torneo_id=torneo_id))


@partido_bp.route("/cargar-datos", methods=["POST"])
def cargar_datos(torneo_id):
    partido_id = request.form.get("partido_id", type=int)
    ganador_id = request.form.get("ganador_id", type=int)
    peleador1_id = request.form.get("peleador1_id", type=int)
    peleador2_id = request.form.get("peleador2_id", type=int)
    rondas_jugadas = request.form.get("rondas_jugadas", type=int)
    try:
        partido_service.cargar_resultado(
            partido_id, ganador_id, peleador1_id, peleador2_id, rondas_jugadas
        )
    except partido_service.PartidoInvalidoError as e:
        flash(str(e))
    return redirect(url_for("partido.actual", torneo_id=torneo_id))


@partido_bp.route("/bracket", methods=["GET", "POST"])
def bracket(torneo_id):
    bracket_actual = partido_service.obtener_bracket(torneo_id)
    nombres = _nombres_jugadores()
    clasificados_ids = sorted({
        jid for p in bracket_actual for jid in (p["jugador1_id"], p["jugador2_id"])
    }, key=lambda jid: nombres.get(jid, ""))
    clasificados = [{"id": jid, "nombre": nombres.get(jid)} for jid in clasificados_ids]

    if request.method == "GET":
        return render_template(
            "partidos/bracket.html", torneo_id=torneo_id, bracket=bracket_actual, clasificados=clasificados
        )

    emparejamientos = []
    i = 0
    while request.form.get(f"jugador1_{i}") is not None:
        emparejamientos.append([
            request.form.get(f"jugador1_{i}", type=int),
            request.form.get(f"jugador2_{i}", type=int),
        ])
        i += 1

    try:
        partido_service.resembrar_bracket(torneo_id, emparejamientos)
        return redirect(url_for("partido.actual", torneo_id=torneo_id))
    except partido_service.BracketInvalidoError as e:
        flash(str(e))
        return render_template(
            "partidos/bracket.html", torneo_id=torneo_id, bracket=bracket_actual, clasificados=clasificados
        ), 400


@partido_bp.route("/descartar", methods=["POST"])
def descartar(torneo_id):
    partido_id = request.form.get("partido_id", type=int)
    try:
        partido_service.marcar_no_realizado(partido_id)
    except partido_service.PartidoInvalidoError as e:
        flash(str(e))
    return redirect(url_for("partido.actual", torneo_id=torneo_id))


@partido_bp.route("/forzar", methods=["POST"])
def forzar(torneo_id):
    jugador_id = request.form.get("jugador_id", type=int)
    clasificado = request.form.get("clasificado") == "si"
    observacion = request.form.get("observacion") or None
    try:
        partido_service.forzar_clasificado(torneo_id, jugador_id, clasificado, observacion)
    except partido_service.ClasificacionInvalidaError as e:
        flash(str(e))
    return redirect(url_for("partido.actual", torneo_id=torneo_id))


@partido_bp.route("/reintentar", methods=["POST"])
def reintentar(torneo_id):
    empatados_ids = [int(j) for j in request.form.getlist("jugadores_empatados_ids")]
    slots = request.form.get("slots", type=int)
    try:
        partido_service.reintentar_desempate(torneo_id, empatados_ids, slots)
    except partido_service.ClasificacionInvalidaError as e:
        flash(str(e))
    return redirect(url_for("partido.actual", torneo_id=torneo_id))
