from flask import Flask, request, render_template, g
from flask_wtf.csrf import CSRFProtect

from config import Config
from routes.torneo_routes import torneo_bp
from routes.inicio_routes import inicio_bp
from routes.partido_routes import partido_bp
from routes.jugador_routes import jugador_bp
from routes.configuracion_routes import configuracion_bp
from routes.peleador_routes import peleador_frontend_bp
from routes.admin_routes import admin_bp
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

    # Estado del warmup, cacheado en memoria: una vez que terminó, no se
    # vuelve a preguntar nunca más (el backend no reinicia sin que este
    # proceso también reinicie, en la práctica).
    _warmup_listo = {"si": False}

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
        if request.method != "GET":
            return
        try:
            estado = torneo_service.estado_warmup()
        except Exception:
            _warmup_listo["si"] = True  # backend caído: que entre y vea el error real
            return
        if estado.get("completado"):
            _warmup_listo["si"] = True
            return
        # Se usa el nombre que ya esté en cache, sin pedirlo al backend: la
        # pantalla de carga tiene que renderizar al instante, y el backend
        # está justo ocupado precalculando.
        g.sirviendo_pantalla_de_carga = True
        nombre = torneo_service._cache_nombre_club["valor"] or "App del Torneo"
        return render_template("cargando.html", estado=estado, nombre_club_carga=nombre)

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
