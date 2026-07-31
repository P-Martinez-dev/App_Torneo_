from flask import Flask

from config import Config
from routes.torneo_routes import torneo_bp
from routes.inicio_routes import inicio_bp
from routes.partido_routes import partido_bp
from routes.jugador_routes import jugador_bp
from routes.configuracion_routes import configuracion_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.register_blueprint(inicio_bp)
    app.register_blueprint(torneo_bp)
    app.register_blueprint(partido_bp)
    app.register_blueprint(jugador_bp)
    app.register_blueprint(configuracion_bp)

    app.jinja_env.globals["imagen_url"] = lambda path: (
        f"{Config.API_BASE_URL}/static/{path}" if path else None
    )

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(port=Config.PORT, debug=Config.DEBUG)
