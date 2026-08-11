"""
Mide de dónde sale el tiempo de cada consulta a la base.

Distingue tres cosas que se confunden entre sí:
  1) Cuánto tarda ABRIR una conexión nueva (handshake TCP + TLS)
  2) Cuánto tarda una consulta trivial sobre una conexión YA abierta
  3) Cuánto tarda una consulta pidiendo la conexión al pool cada vez
     (que es exactamente lo que hace la app hoy)

Correr desde la raíz del proyecto, con el venv activado:
    python3 medir_latencia.py
"""
import os
import statistics
import time

from dotenv import load_dotenv
import mysql.connector
from mysql.connector import pooling

load_dotenv(os.path.join("backend", ".env"))

CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
}

REPETICIONES = 5


def _ms(segundos):
    return f"{segundos * 1000:.0f} ms"


def _resumen(nombre, tiempos):
    print(f"{nombre}")
    print(f"   media: {_ms(statistics.mean(tiempos))}   |   min: {_ms(min(tiempos))}   |   max: {_ms(max(tiempos))}")
    print()


print(f"Midiendo contra {CONFIG['host']}:{CONFIG['port']}")
print(f"({REPETICIONES} repeticiones de cada cosa)\n")

# --- 1) Abrir una conexión nueva de cero ---
tiempos = []
for _ in range(REPETICIONES):
    t0 = time.perf_counter()
    conn = mysql.connector.connect(**CONFIG)
    tiempos.append(time.perf_counter() - t0)
    conn.close()
_resumen("1) Abrir una conexion NUEVA (TCP + TLS + login)", tiempos)

# --- 2) Consulta trivial sobre una conexión ya abierta ---
conn = mysql.connector.connect(**CONFIG)
tiempos = []
for _ in range(REPETICIONES):
    t0 = time.perf_counter()
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    cursor.fetchall()
    cursor.close()
    tiempos.append(time.perf_counter() - t0)
conn.close()
_resumen("2) Consulta trivial sobre conexion YA abierta (esto es el RTT puro)", tiempos)

# --- 3) Consulta pidiendo la conexión al pool cada vez (como hace la app) ---
pool = pooling.MySQLConnectionPool(pool_name="medicion", pool_size=5, **CONFIG)
tiempos = []
for _ in range(REPETICIONES):
    t0 = time.perf_counter()
    conn = pool.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    cursor.fetchall()
    cursor.close()
    conn.close()
    tiempos.append(time.perf_counter() - t0)
_resumen("3) Consulta pidiendo conexion AL POOL cada vez (lo que hace la app)", tiempos)

# --- 4) Una consulta real del proyecto, para comparar contra las triviales ---
conn = pool.get_connection()
tiempos = []
for _ in range(REPETICIONES):
    t0 = time.perf_counter()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT nombre_club FROM configuracion_general WHERE id = 1")
    cursor.fetchall()
    cursor.close()
    tiempos.append(time.perf_counter() - t0)
conn.close()
_resumen("4) La consulta real de 'nombre-club' (conexion ya abierta)", tiempos)

print("--- Como leer esto ---")
print("Si (2) da ~150-250ms  -> la distancia a la base es la normal para San Francisco.")
print("Si (3) es MUCHO mayor que (2) -> el pool esta reconectando en vez de reusar.")
print("Si (2) ya da >1s -> el problema es la distancia/red, no el codigo.")
print()

# --- 5) La forma que usa la app AHORA (backend/database/db.py) ---
import sys
sys.path.insert(0, "backend")
try:
    from database.db import get_connection
except ImportError as e:
    print(f"(No se pudo medir el metodo de la app: {e})")
else:
    tiempos = []
    for _ in range(REPETICIONES):
        t0 = time.perf_counter()
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT nombre_club FROM configuracion_general WHERE id = 1")
        cursor.fetchall()
        cursor.close()
        conn.close()
        tiempos.append(time.perf_counter() - t0)
    print("=" * 60)
    _resumen("5) La MISMA consulta, con el metodo que usa la app ahora", tiempos)
    print("Comparar (5) contra (3): esa es la mejora.")
    print("Lo mas bajo posible es (2), que es el viaje puro y no se puede evitar.")