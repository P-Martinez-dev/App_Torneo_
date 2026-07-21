import os
import mysql.connector
from mysql.connector import Error


def get_connection():
    """
    Crea y devuelve una nueva conexión a MySQL.
    Se llama por función (no a nivel de módulo) para que las
    variables de entorno estén disponibles en el momento del request.
    """
    try:
        return mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
        )
    except Error as e:
        raise RuntimeError(f"No se pudo conectar a la base de datos: {e}")