from database.db import get_connection
from models.grupo import Grupo


def crear(torneo_id, nombre, tipo="grupo", slots_a_clasificar=None, grupo_padre_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO grupo (torneo_id, nombre, tipo, slots_a_clasificar, grupo_padre_id)
           VALUES (%s, %s, %s, %s, %s)""",
        (torneo_id, nombre, tipo, slots_a_clasificar, grupo_padre_id),
    )
    conn.commit()
    nuevo_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return nuevo_id


def obtener_desempate_interno(grupo_padre_id):
    """Devuelve el mini-grupo de desempate interno de un grupo (si existe).
    Puede haber más de uno si se reintentó varias veces (cada 'Reintentar'
    arma uno nuevo apuntando al mismo padre) -- por eso se toma el más
    reciente, que es el que tiene la resolución vigente."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM grupo WHERE grupo_padre_id = %s AND tipo = 'desempate' ORDER BY id DESC LIMIT 1",
        (grupo_padre_id,),
    )
    fila = cursor.fetchone()
    cursor.close()
    conn.close()
    return Grupo.from_row(fila)


def obtener_por_id(grupo_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM grupo WHERE id = %s", (grupo_id,))
    fila = cursor.fetchone()
    cursor.close()
    conn.close()
    return Grupo.from_row(fila)


def obtener_por_torneo(torneo_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM grupo WHERE torneo_id = %s ORDER BY id", (torneo_id,))
    filas = cursor.fetchall()
    cursor.close()
    conn.close()
    return [Grupo.from_row(f) for f in filas]