import requests
from flask import Flask, request, render_template, g, flash, url_for
from flask_wtf.csrf import CSRFProtect

from config import Config
from routes.torneo_routes import torneo_bp
from routes.inicio_routes import inicio_bp
from routes.partido_routes import partido_bp
from routes.jugador_routes import jugador_bp
from routes.configuracion_routes import configuracion_bp
from routes.peleador_routes import peleador_frontend_bp
from routes.admin_routes import admin_bp
from routes.enfrentamiento_routes import enfrentamiento_bp
from auth import es_admin
from markdown_simple import markdown_a_html
from services import torneo_service


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CSRFProtect(app)

    app.register_blueprint(inicio_bp)
    app.register_blueprint(torneo_bp)
    app.register_blueprint(partido_bp)
    app.register_blueprint(jugador_bp)
    app.register_blueprint(configuracion_bp)
    app.register_blueprint(peleador_frontend_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(enfrentamiento_bp)

    # Estado del warmup, cacheado en memoria: una vez que terminó, no se
    # vuelve a preguntar. Ojo: en Render los dos servicios se duermen por
    # separado, así que el backend SÍ puede reiniciarse con este proceso
    # vivo -- por eso el manejador de errores de conexión de más abajo lo
    # vuelve a poner en False, y la pantalla de carga reaparece sola.
    _warmup_listo = {"si": False}

    PASO_DESPERTANDO = "Despertando el servidor..."
    # Estado con el que se muestra la pantalla de carga cuando el backend no
    # contestó. Misma forma que lo que devuelve /estado-carga en ese caso
    # (ver inicio_routes.py): 'sin_respuesta' es lo que le dice a la
    # pantalla que tiene que despertarlo.
    ESTADO_SIN_RESPUESTA = {"paso_actual": PASO_DESPERTANDO, "sin_respuesta": True}

    # Errores HTTP del backend que significan "todavía no está disponible"
    # y no "hay un bug": 502/503/504 los devuelve Render mientras lo
    # despierta, y 429 lo devuelve Render cuando limita los pedidos de este
    # servidor (ver api_client.py). Cualquier otro código sigue saliendo
    # como error, para que se vea.
    CODIGOS_BACKEND_NO_DISPONIBLE = (429, 502, 503, 504)

    # Métodos que solo leen: ahí se puede mostrar la pantalla de carga y
    # después recargar la misma página sin riesgo. HEAD es un GET sin cuerpo
    # (lo usan los chequeos de Render, entre otros); sin incluirlo, un HEAD
    # con el backend dormido terminaba en un 500.
    METODOS_DE_LECTURA = ("GET", "HEAD")

    def _pantalla_de_carga(estado, url_destino=None):
        """La pantalla de carga, desde cualquier lugar que la necesite.
        url_destino: adónde ir cuando el backend esté listo. Sin él, la
        pantalla recarga la página pedida (lo normal en un GET); con un
        POST eso reenviaría el formulario, así que ahí se manda a otra
        página."""
        # Se usa el nombre que ya esté en cache, sin pedirlo al backend: la
        # pantalla de carga tiene que renderizar al instante, y el backend
        # está justo ocupado precalculando (o dormido).
        g.sirviendo_pantalla_de_carga = True
        nombre = torneo_service._cache_nombre_club["valor"] or "App del Torneo"
        # Una dirección del backend para que el NAVEGADOR lo despierte con un
        # pedido propio (ver cargando.html). Cualquier ruta sirve: a Render
        # le alcanza con que llegue un pedido para levantar el servicio,
        # aunque el backend después lo rechace por no traer la clave
        # interna -- la clave no se manda nunca al navegador.
        url_despertar = f"{Config.API_BASE_URL}/torneos/warmup/progreso"
        return render_template(
            "cargando.html", estado=estado, nombre_club_carga=nombre,
            url_destino=url_destino, url_despertar=url_despertar,
        )

    @app.before_request
    def mostrar_pantalla_de_carga_si_hace_falta():
        """Si el backend todavía está precalculando, se devuelve la pantalla
        de carga en vez de la página pedida. Está ANTES de que la vista
        intente traer datos: si no, la página quedaría esperando al backend
        ocupado y la pantalla de carga aparecería recién cuando ya no hace
        falta (que es justo lo que pasaba antes)."""
        if _warmup_listo["si"]:
            return
        if request.endpoint in ("static", "inicio.estado_carga"):
            return
        if request.method not in METODOS_DE_LECTURA:
            return
        try:
            estado = torneo_service.estado_warmup()
        except Exception:
            # Antes esto marcaba "listo" para que se viera el error real --
            # pero en Render lo normal es que el backend esté DORMIDO, no
            # caído: tarda en despertar y esta consulta vence antes. Marcar
            # "listo" dejaba pasar a la vista, que fallaba con un 500, y la
            # pantalla de carga no volvía a aparecer nunca más. Ahora se
            # espera en la pantalla de carga (que corta sola con un mensaje
            # si el backend de verdad no vuelve).
            return _pantalla_de_carga(ESTADO_SIN_RESPUESTA)
        if estado.get("completado"):
            _warmup_listo["si"] = True
            return
        return _pantalla_de_carga(estado)

    def _backend_no_disponible(e):
        """Cualquier pedido al backend que no llegó a responder (dormido,
        arrancando, Render devolviendo 502/503/504 mientras lo despierta, o
        429 / pausa por 429 cuando Render limita los pedidos) termina acá, en un solo lugar, en vez de un 500 en cada ruta -- mismo
        criterio que la invalidación de cache del backend: centralizado, así
        una ruta nueva no puede olvidarse de manejarlo.

        Cualquier otro error del backend (un 500 por un bug, un 404 que la
        ruta no esperaba) NO se tapa: sigue saliendo como error, para que se
        vea y se arregle."""
        if isinstance(e, requests.exceptions.HTTPError):
            if e.response is None or e.response.status_code not in CODIGOS_BACKEND_NO_DISPONIBLE:
                raise e
        _warmup_listo["si"] = False
        if request.method in METODOS_DE_LECTURA:
            return _pantalla_de_carga(ESTADO_SIN_RESPUESTA), 503
        # En un POST no se puede saber si el backend llegó a guardar el
        # cambio antes de que se cortara la espera (con un timeout de
        # lectura, pudo haberlo hecho). Se avisa, y se vuelve a la página
        # del formulario en vez de reenviarlo a ciegas.
        flash("El servidor tardó en responder y no se pudo confirmar el cambio. "
              "Revisá si quedó guardado antes de volver a intentarlo.")
        destino = request.referrer or url_for("inicio.inicio")
        return _pantalla_de_carga(ESTADO_SIN_RESPUESTA, url_destino=destino), 503

    app.register_error_handler(requests.exceptions.ConnectionError, _backend_no_disponible)
    app.register_error_handler(requests.exceptions.Timeout, _backend_no_disponible)
    app.register_error_handler(requests.exceptions.HTTPError, _backend_no_disponible)

    def imagen_url(path):
        """Las imágenes pueden venir de dos lados: guardadas en la nube
        (viene la URL completa, se usa tal cual) o en el disco del backend
        (viene una ruta relativa, hay que armarle la URL). Soportar las dos
        permite migrar de a poco, sin romper las que ya estaban."""
        if not path:
            return None
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"{Config.API_BASE_URL}/static/{path}"

    app.jinja_env.globals["imagen_url"] = imagen_url
    # Los modos y fases se guardan con su nombre técnico (en minúscula y con
    # guiones bajos). Acá se traduce al nombre que se muestra en pantalla, en
    # un único lugar: si mañana se agrega un modo nuevo y se olvida sumarlo
    # acá, muestra el técnico con espacios en vez de romperse.
    NOMBRES_VISIBLES = {
        "rey_de_la_cancha": "Rey de la cancha",
        "todos_contra_todos": "Todos contra todos",
        "grupos_eliminacion": "Grupos + eliminación",
        "tercer_puesto": "Tercer puesto",
        "eliminacion": "Eliminación",
        "grupos": "Grupos",
    }

    def nombre_modo(valor):
        if not valor:
            return ""
        return NOMBRES_VISIBLES.get(valor, valor.replace("_", " "))

    app.jinja_env.filters["nombre_modo"] = nombre_modo

    app.jinja_env.globals["es_admin"] = es_admin
    app.jinja_env.filters["markdown"] = markdown_a_html

    @app.context_processor
    def inyectar_nombre_club():
        """Disponible en TODAS las plantillas (el wordmark del header
        vive en base.html, que todas extienden) -- si el backend no
        responde por algún motivo, no rompe la página, solo usa el
        nombre por defecto."""
        # Mientras se muestra la pantalla de carga NO se le pide nada al
        # backend: está ocupado precalculando, y esa pantalla tiene que
        # aparecer al instante.
        if getattr(g, "sirviendo_pantalla_de_carga", False):
            return {"nombre_club": torneo_service._cache_nombre_club["valor"] or "App del Torneo"}
        try:
            nombre = torneo_service.obtener_nombre_club()
        except Exception:
            nombre = "App del Torneo"
        return {"nombre_club": nombre}

    return app


# gunicorn (y cualquier servidor WSGI de producción) importa este archivo y
# busca una variable llamada 'app' a nivel de módulo -- nunca ejecuta el
# bloque de abajo. En tu compu seguís corriendo 'python app.py' normal,
# esto no cambia nada de cómo trabajás en local.
app = create_app()

if __name__ == "__main__":
    app.run(port=Config.PORT, debug=Config.DEBUG)
