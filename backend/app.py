from flask import Flask, request, jsonify

from config import Config
from controllers.jugador_routes import jugador_bp
from controllers.torneo_routes import torneo_bp
from controllers.partido_routes import partido_bp
from controllers.peleador_routes import peleador_bp
from controllers.admin_routes import admin_bp
from services import cache_resultados


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

    @app.after_request
    def invalidar_cache_si_hubo_cambios(response):
        """Cualquier escritura que haya salido bien invalida todo lo
        cacheado. Está puesto acá, en un solo lugar, y no endpoint por
        endpoint: así no hay forma de agregar una ruta nueva que modifique
        datos y olvidarse de invalidar (que sería un bug silencioso, de los
        que muestran datos viejos sin avisar)."""
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and response.status_code < 400:
            cache_resultados.invalidar_todo()
        return response

    app.register_blueprint(jugador_bp)
    app.register_blueprint(torneo_bp)
    app.register_blueprint(partido_bp)
    app.register_blueprint(peleador_bp)
    app.register_blueprint(admin_bp)

    # Calienta el cache al arrancar -- así el primer usuario ya encuentra
    # todo precalculado. El progreso queda disponible en /torneos/warmup/progreso
    # El warmup se lanza al atender el primer pedido, no al importar el
    # módulo: bajo gunicorn, la importación ocurre en un proceso y los
    # pedidos se atienden en otro, así que si se lanza acá el estado
    # queda en el proceso equivocado y el frontend nunca lo ve avanzar.
    _warmup_lanzado = {"si": False}

    @app.before_request
    def _lanzar_warmup_una_vez():
        if not _warmup_lanzado["si"]:
            _warmup_lanzado["si"] = True
            cache_resultados.calentar(app)

    return app


# gunicorn (y cualquier servidor WSGI de producción) importa este archivo y
# busca una variable llamada 'app' a nivel de módulo -- nunca ejecuta el
# bloque de abajo. En tu compu seguís corriendo 'python app.py' normal,
# esto no cambia nada de cómo trabajás en local.
app = create_app()

if __name__ == "__main__":
    app.run(port=Config.PORT, debug=Config.DEBUG)