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