from flask import Flask

from config import Config
from controllers.jugador_routes import jugador_bp
from controllers.torneo_routes import torneo_bp
from controllers.partido_routes import partido_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.register_blueprint(jugador_bp)
    app.register_blueprint(torneo_bp)
    app.register_blueprint(partido_bp)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(port=Config.PORT, debug=Config.DEBUG)