import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """
    Configuración de la app Flask. A diferencia de las variables que usa
    db.py (que se leen por función para evitar el problema de evaluación
    a nivel de módulo antes de load_dotenv), estas sí se pueden leer acá
    porque config.py se importa DESPUÉS de load_dotenv() en este mismo archivo.
    """
    DEBUG = os.getenv("FLASK_DEBUG", "True") == "True"
    PORT = int(os.getenv("FLASK_PORT", 5000))
    SECRET_KEY = os.getenv("SECRET_KEY", "dev")
    # Clave compartida con el frontend -- el backend rechaza cualquier
    # pedido que no la traiga (ver middleware en app.py). Así nadie puede
    # pegarle directo a la API salteándose el login del frontend, ni
    # aunque el backend termine expuesto en su propia URL pública.
    INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "dev-key-cambiar-en-produccion")
    # Límite global de subida (además del chequeo de 5MB por imagen en
    # jugador_service) para no dejar que Werkzeug cargue en memoria un
    # archivo gigante antes de que nuestra propia validación lo rechace.
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB