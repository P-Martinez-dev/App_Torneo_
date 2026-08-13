import os
import threading
import time

import mysql.connector
from mysql.connector import Error
from mysql.connector.constants import ClientFlag

# Si la conexión estuvo un rato sin usarse, antes de reusarla se verifica
# que siga viva. Ese chequeo cuesta un viaje entero a la base, así que
# solo se hace cuando de verdad pudo haberse caído por inactividad -- no
# en cada consulta.
_SEGUNDOS_SIN_USO_PARA_VERIFICAR = 60

_local = threading.local()


class _ConexionReusada:
    """
    Envuelve la conexión real para que close() NO la cierre.

    Todos los repositorios del proyecto llaman conn.close() al terminar
    cada consulta. Contra una base local eso no costaba nada, pero contra
    una remota, abrir una conexión cuesta ~4 veces lo que cuesta la
    consulta en sí (medido: ~1570ms abrir vs ~427ms consultar). Entonces
    close() la deja viva para el próximo pedido, y el resto del proyecto
    sigue exactamente igual, sin tocar ni un repositorio.
    """

    def __init__(self, cnx):
        self._cnx = cnx

    def __getattr__(self, nombre):
        # Todo lo demás (cursor, commit, etc.) va directo a la conexión real
        return getattr(self._cnx, nombre)

    def close(self):
        # Red de seguridad: si una operación de varias escrituras falló a
        # mitad de camino y dejó su transacción abierta, se descarta antes
        # de que la conexión se reuse, para que la próxima consulta no
        # arrastre estado sucio. Con autocommit activado, una lectura nunca
        # deja nada abierto, así que esto casi nunca llega a ejecutarse
        # (preguntar si hay transacción abierta no cuesta ningún viaje).
        try:
            if self._cnx.in_transaction:
                self._cnx.rollback()
        except Error:
            pass
        _local.ultimo_uso = time.time()


def _config():
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", 3306)),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME"),
        # Sin autocommit, hasta un SELECT abre una transaccion que despues hay
        # que cerrar -- y cada cierre cuesta un viaje entero a la base. Las
        # pocas operaciones que necesitan varias escrituras atomicas abren su
        # transaccion explicitamente (ver conn.start_transaction() en los
        # repositorios), asi que no se pierde ninguna garantia.
        "autocommit": True,
        # Por defecto, MySQL informa cuántas filas CAMBIARON en un UPDATE.
        # Todo el proyecto usa ese número para saber si la fila existía
        # ("¿actualicé algo o no había nada con ese id?"), así que guardar
        # sin modificar nada daba 0 y se interpretaba como "no existe" ->
        # 404. Con FOUND_ROWS informa cuántas COINCIDIERON, que es lo que
        # el código realmente quiere preguntar. No afecta a DELETE.
        "client_flags": [ClientFlag.FOUND_ROWS],
        # Sin esto, una conexión bloqueada por firewall se cuelga para
        # siempre en silencio, sin error ni timeout -- que es exactamente
        # lo que dejaba el warmup congelado en 0% sin ninguna pista.
        "connection_timeout": 15,
        # El timeout de arriba cubre solo el ESTABLECER la conexión. Si la
        # conexión entra bien pero la consulta nunca vuelve, hace falta este
        # otro: sin él, el hilo se queda esperando una respuesta que no llega.
        "read_timeout": 30,
        
    }


def _abrir_conexion():
    cnx = mysql.connector.connect(**_config())
    _local.cnx = cnx
    _local.ultimo_uso = time.time()
    return cnx


def _descartar_conexion():
    cnx = getattr(_local, "cnx", None)
    if cnx is not None:
        try:
            cnx.close()
        except Error:
            pass
    _local.cnx = None


def get_connection():
    print(">>> DB: pidiendo conexión", flush=True)
    """
    Devuelve una conexión lista para usar, reusando la misma mientras
    siga viva (una por hilo). El código que la usa no cambia en nada:
    se sigue llamando get_connection() y conn.close() como siempre.
    """
    cnx = getattr(_local, "cnx", None)

    if cnx is not None:
        inactiva_hace = time.time() - getattr(_local, "ultimo_uso", 0)
        if inactiva_hace < _SEGUNDOS_SIN_USO_PARA_VERIFICAR:
            return _ConexionReusada(cnx)
        try:
            cnx.ping(reconnect=True, attempts=1, delay=0)
            _local.ultimo_uso = time.time()
            return _ConexionReusada(cnx)
        except Error:
            _descartar_conexion()

    try:
        return _ConexionReusada(_abrir_conexion())
    except Error as e:
        raise RuntimeError(f"No se pudo conectar a la base de datos: {e}")
