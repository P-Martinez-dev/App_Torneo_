from database.db import get_connection


def crear(torneo_id, nombre):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO grupo (torneo_id, nombre) VALUES (%s, %s)", (torneo_id, nombre)
    )
    conn.commit()
    nuevo_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return nuevo_id


def obtener_por_torneo(torneo_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM grupo WHERE torneo_id = %s ORDER BY id", (torneo_id,))
    filas = cursor.fetchall()
    cursor.close()
    conn.close()
    return filas