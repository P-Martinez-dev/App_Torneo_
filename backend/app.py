from flask import Flask, request, jsonify

from config import Config
from controllers.jugador_routes import jugador_bp
from controllers.torneo_routes import torneo_bp
from controllers.partido_routes import partido_bp
from controllers.peleador_routes import peleador_bp
from controllers.admin_routes import admin_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    @app.before_request
    def exigir_clave_interna():
        """Rechaza cualquier pedido que no traiga la clave compartida con
        el frontend -- así, aunque este backend termine con una URL
        pública propia (según cómo se aloje), nadie puede pegarle
        directo saltándose el login del frontend. El frontend la manda
        sola en cada pedido (ver services/api_client.py).

        Excepción: los archivos de static/ (las imágenes de jugador y
        peleador) los pide el NAVEGADOR directo con un <img src="...">,
        no el frontend -- esos pedidos nunca van a traer la clave, y no
        hace falta que la traigan (son archivos públicos igual)."""
        if request.endpoint == "static":
            return
        clave = request.headers.get("X-Internal-Key")
        if clave != Config.INTERNAL_API_KEY:
            return jsonify({"error": "No autorizado"}), 401

    app.register_blueprint(jugador_bp)
    app.register_blueprint(torneo_bp)
    app.register_blueprint(partido_bp)
    app.register_blueprint(peleador_bp)
    app.register_blueprint(admin_bp)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(port=Config.PORT, debug=Config.DEBUG)