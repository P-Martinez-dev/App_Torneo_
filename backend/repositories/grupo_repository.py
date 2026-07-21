from database.db import get_connection
from models.grupo import Grupo


def crear(torneo_id, nombre, tipo="grupo", slots_a_clasificar=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO grupo (torneo_id, nombre, tipo, slots_a_clasificar)
           VALUES (%s, %s, %s, %s)""",
        (torneo_id, nombre, tipo, slots_a_clasificar),
    )
    conn.commit()
    nuevo_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return nuevo_id


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