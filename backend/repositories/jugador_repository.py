from database.db import get_connection


def obtener_todos():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM jugador ORDER BY nombre")
    filas = cursor.fetchall()
    cursor.close()
    conn.close()
    return filas


def obtener_por_id(jugador_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM jugador WHERE id = %s", (jugador_id,))
    fila = cursor.fetchone()
    cursor.close()
    conn.close()
    return fila


def crear(nombre, fecha_nacimiento):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO jugador (nombre, fecha_nacimiento) VALUES (%s, %s)",
        (nombre, fecha_nacimiento),
    )
    conn.commit()
    nuevo_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return nuevo_id


def actualizar(jugador_id, nombre, fecha_nacimiento):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE jugador SET nombre = %s, fecha_nacimiento = %s WHERE id = %s",
        (nombre, fecha_nacimiento, jugador_id),
    )
    conn.commit()
    filas_afectadas = cursor.rowcount
    cursor.close()
    conn.close()
    return filas_afectadas > 0


def eliminar(jugador_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM jugador WHERE id = %s", (jugador_id,))
    conn.commit()
    filas_afectadas = cursor.rowcount
    cursor.close()
    conn.close()
    return filas_afectadas > 0