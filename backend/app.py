from flask import Flask
from controllers.jugador_routes import jugador_bp

app = Flask(__name__)
app.register_blueprint(jugador_bp)

if __name__ == "__main__":
    app.run(port=5000, debug=True)