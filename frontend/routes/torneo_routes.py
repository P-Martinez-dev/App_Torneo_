from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from services import torneo_service, jugador_service
from auth import requiere_admin

torneo_bp = Blueprint("torneo", __name__, url_prefix="/torneos")


@torneo_bp.route("/estadisticas-generales")
def estadisticas_generales():
    generales = torneo_service.obtener_estadisticas_generales()
    return render_template("torneos/estadisticas_generales.html", generales=generales)


@torneo_bp.route("/tabla-general/exportar-imagen")
def exportar_imagen_tabla_general():
    excluidos_ids = request.args.getlist("excluir", type=int)
    imagen = torneo_service.exportar_imagen_tabla_general(excluidos_ids)
    return Response(imagen, mimetype="image/png", headers={
        "Content-Disposition": 'attachment; filename="ranking_general.png"'
    })


@torneo_bp.route("/explorar")
def explorar():
    torneos = torneo_service.listar_torneos()
    return render_template("torneos/explorar.html", torneos=torneos)


@torneo_bp.route("/info")
def info():
    infos = torneo_service.obtener_infos()
    return render_template("torneos/info.html", texto=infos["info_formatos"], cual="formatos",
                           titulo="Cómo funciona cada formato", eyebrow="Torneos",
                           volver=url_for("torneo.explorar"))


@torneo_bp.route("/info-tablas")
def info_tablas():
    infos = torneo_service.obtener_infos()
    return render_template("torneos/info.html", texto=infos["info_tablas"], cual="tablas",
                           titulo="Cómo se arma la tabla", eyebrow="Tablas",
                           volver=url_for("torneo.listado"))


@torneo_bp.route("/info/<string:cual>/editar", methods=["GET", "POST"])
@requiere_admin
def editar_info(cual):
    if cual not in ("tablas", "formatos"):
        flash("Esa info no existe.")
        return redirect(url_for("inicio.inicio"))

    volver = url_for("torneo.info_tablas") if cual == "tablas" else url_for("torneo.info")

    if request.method == "POST":
        torneo_service.actualizar_info(cual, request.form.get("texto"))
        flash("Info actualizada.")
        return redirect(volver)

    infos = torneo_service.obtener_infos()
    texto = infos["info_tablas"] if cual == "tablas" else infos["info_formatos"]
    return render_template("torneos/info_editar.html", texto=texto, cual=cual, volver=volver,
                           titulo="Cómo se arma la tabla" if cual == "tablas" else "Cómo funciona cada formato")


@torneo_bp.route("")
def listado():
    torneos = torneo_service.listar_torneos()
    excluidos_ids = request.args.getlist("excluir", type=int)
    tabla = torneo_service.tabla_general(excluidos_ids)
    return render_template(
        "torneos/listado.html", torneos=torneos, tabla_general=tabla, excluidos_ids=excluidos_ids,
    )


@torneo_bp.route("/<int:torneo_id>/exportar-imagen")
def exportar_imagen(torneo_id):
    imagen = torneo_service.exportar_imagen(torneo_id)
    return Response(imagen, mimetype="image/png", headers={
        "Content-Disposition": f'attachment; filename="torneo_{torneo_id}.png"'
    })


@torneo_bp.route("/<int:torneo_id>")
def detalle(torneo_id):
    resumen = torneo_service.obtener_resumen(torneo_id)
    estadisticas = torneo_service.obtener_estadisticas(torneo_id)
    navegacion = torneo_service.obtener_navegacion(torneo_id)
    return render_template(
        "torneos/detalle.html", torneo_id=torneo_id, resumen=resumen, estadisticas=estadisticas,
        navegacion=navegacion,
    )


@torneo_bp.route("/<int:torneo_id>/editar", methods=["GET", "POST"])
@requiere_admin
def editar(torneo_id):
    torneo = torneo_service.obtener_torneo(torneo_id)
    if torneo is None:
        flash("Ese torneo no existe.")
        return redirect(url_for("torneo.listado"))

    if request.method == "GET":
        return render_template("torneos/editar.html", torneo=torneo, error=None)

    try:
        descripcion = (request.form.get("descripcion") or "").strip() or None
        lugar = (request.form.get("lugar") or "").strip() or None
        torneo_service.actualizar_torneo(
            torneo_id, request.form.get("nombre"), request.form.get("fecha"), descripcion, lugar
        )
        return redirect(url_for("torneo.detalle", torneo_id=torneo_id))
    except torneo_service.TorneoInvalidoError as e:
        return render_template("torneos/editar.html", torneo=torneo, error=str(e)), 400


@torneo_bp.route("/<int:torneo_id>/eliminar-definitivo", methods=["POST"])
@requiere_admin
def eliminar_definitivo(torneo_id):
    """Eliminar desde la pantalla de detalle (cualquier estado) -- distinto
    del /eliminar que usa Inicio para descartar un torneo en desarrollo,
    porque el destino después de borrar es otro (acá vuelve a Tablas)."""
    torneo_service.eliminar_torneo(torneo_id)
    return redirect(url_for("torneo.listado"))


@torneo_bp.route("/<int:torneo_id>/eliminar", methods=["POST"])
@requiere_admin
def eliminar(torneo_id):
    """Se usa desde el diálogo de 'descartar el torneo en desarrollo' en Inicio."""
    torneo_service.eliminar_torneo(torneo_id)
    return redirect(url_for("torneo.crear"))


@torneo_bp.route("/nuevo", methods=["GET", "POST"])
@requiere_admin
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
