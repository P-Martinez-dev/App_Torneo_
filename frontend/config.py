import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """
    Configuración de la app Flask del frontend. Igual que en el backend,
    load_dotenv() corre antes que estas lecturas porque están en el mismo
    módulo, así que es seguro leerlas acá arriba (a diferencia de
    API_BASE_URL usado dentro de los repositories, que se lee por función
    en el momento de la llamada, mismo criterio que db.py en el backend).
    """
    DEBUG = os.getenv("FLASK_DEBUG", "True") == "True"
    PORT = int(os.getenv("FLASK_PORT", 3000))
    SECRET_KEY = os.getenv("SECRET_KEY", "dev")
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5000")
    # Misma clave que el backend -- ver INTERNAL_API_KEY en backend/config.py
    INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "dev-key-cambiar-en-produccion")
