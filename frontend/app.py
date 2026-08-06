from flask import Flask
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

    app.jinja_env.globals["imagen_url"] = lambda path: (
        f"{Config.API_BASE_URL}/static/{path}" if path else None
    )
    app.jinja_env.globals["es_admin"] = es_admin

    @app.context_processor
    def inyectar_nombre_club():
        """Disponible en TODAS las plantillas (el wordmark del header
        vive en base.html, que todas extienden) -- si el backend no
        responde por algún motivo, no rompe la página, solo usa el
        nombre por defecto."""
        try:
            nombre = torneo_service.obtener_nombre_club()
        except Exception:
            nombre = "App del Torneo"
        return {"nombre_club": nombre}

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(port=Config.PORT, debug=Config.DEBUG)
