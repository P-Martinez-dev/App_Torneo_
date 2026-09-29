import os
import threading
import time

import mysql.connector
from mysql.connector import Error
from mysql.connector import errors as errores_mysql
from mysql.connector.constants import ClientFlag

# Si la conexión estuvo este tiempo sin usarse, NO se reusa: se cierra y se
# abre una nueva.
#
# Antes acá se hacía ping() para ver si seguía viva, pero eso tiene una
# trampa: en la nube, una conexión TCP que queda un rato quieta suele
# cortarse SIN AVISO en el camino (ni Render ni Aiven se enteran). Sobre
# una conexión así el ping no falla, se queda esperando una respuesta que
# nunca llega hasta que vence read_timeout -- 30 s, justo el límite de
# gunicorn, que mataba al worker a mitad del pedido. Cerrar la vieja es
# instantáneo aunque esté cortada, y abrir una nueva cuesta ~1,5 s contra
# Aiven: un poco más que un ping sano, pero nunca se traba.
_SEGUNDOS_SIN_USO_PARA_RENOVAR = 60

# Errores que dicen que la CONEXIÓN no sirve más (se perdió, el servidor no
# responde, venció el timeout), a diferencia de un error de la consulta en
# sí (SQL mal escrito, clave duplicada). Ante uno de estos, la conexión se
# descarta para que el próximo pedido abra una nueva en vez de reusar la
# muerta. Si alguno de estos no era de conexión (ej: un deadlock), lo único
# que se pierde es reabrir una conexión de más.
_ERRORES_DE_CONEXION = (errores_mysql.OperationalError, errores_mysql.InterfaceError)

_local = threading.local()


def _vigilado(cnx, funcion):
    """Envuelve una llamada a la conexión o a un cursor: si falla por un
    error de conexión, descarta esa conexión y deja pasar el error igual
    (el pedido que falló sigue fallando -- lo que cambia es que el
    siguiente ya no hereda la conexión muerta)."""
    def envuelta(*args, **kwargs):
        try:
            return funcion(*args, **kwargs)
        except _ERRORES_DE_CONEXION:
            _descartar_si_es_la_actual(cnx)
            raise
    return envuelta


class _CursorVigilado:
    """Un cursor normal, salvo que sus llamadas (execute, fetchall...)
    pasan por _vigilado. Los atributos (rowcount, lastrowid) pasan tal
    cual."""

    def __init__(self, cursor, cnx):
        self._cursor = cursor
        self._cnx = cnx

    def __getattr__(self, nombre):
        atributo = getattr(self._cursor, nombre)
        return _vigilado(self._cnx, atributo) if callable(atributo) else atributo

    def __iter__(self):
        return iter(self._cursor)



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
        # Todo lo demás (cursor, commit, etc.) va a la conexión real, pero
        # vigilado: si falla porque la conexión murió, se descarta. Los
        # cursores que se piden se vigilan igual, que es donde de verdad se
        # entera uno de que la conexión se cayó (en el execute).
        atributo = getattr(self._cnx, nombre)
        if not callable(atributo):
            return atributo
        llamada = _vigilado(self._cnx, atributo)
        if nombre == "cursor":
            return lambda *args, **kwargs: _CursorVigilado(llamada(*args, **kwargs), self._cnx)
        return llamada

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
        # Va por DEBAJO de los 30 s de gunicorn (y de los 25 s con los que el
        # frontend deja de esperar): así, si algo se cuelga, corta este
        # timeout con un error normal y la conexión se descarta -- en vez de
        # que gunicorn mate al worker entero a mitad del pedido.
        "read_timeout": 20,
        
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
            cnx.close()  # instantáneo aunque la conexión esté cortada (medido)
        except Error:
            pass
    _local.cnx = None


def _descartar_si_es_la_actual(cnx):
    """Descarta cnx si todavía es la conexión de este hilo. Si ya se había
    reemplazado por otra, esa otra está sana y no se toca."""
    if getattr(_local, "cnx", None) is cnx:
        _descartar_conexion()


def get_connection():
    """
    Devuelve una conexión lista para usar, reusando la misma mientras
    siga viva (una por hilo). El código que la usa no cambia en nada:
    se sigue llamando get_connection() y conn.close() como siempre.
    """
    cnx = getattr(_local, "cnx", None)

    if cnx is not None:
        inactiva_hace = time.time() - getattr(_local, "ultimo_uso", 0)
        if inactiva_hace < _SEGUNDOS_SIN_USO_PARA_RENOVAR:
            return _ConexionReusada(cnx)
        # Quieta demasiado tiempo: puede estar cortada sin que nadie lo
        # sepa, y verificarlo con ping() puede trabarse (ver arriba).
        _descartar_conexion()

    try:
        return _ConexionReusada(_abrir_conexion())
    except Error as e:
        raise RuntimeError(f"No se pudo conectar a la base de datos: {e}")