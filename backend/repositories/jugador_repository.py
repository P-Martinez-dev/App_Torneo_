from database.db import get_connection
from models.jugador import Jugador


def obtener_ids_existentes(jugadores_ids):
    """Subconjunto de jugadores_ids que efectivamente existen en la tabla.
    Se usa para validar antes de insertar (evita el 500 de MySQL por FK
    violation cuando llega un id inexistente, y da un mensaje claro)."""
    if not jugadores_ids:
        return set()
    conn = get_connection()
    cursor = conn.cursor()
    placeholders = ",".join(["%s"] * len(jugadores_ids))
    cursor.execute(f"SELECT id FROM jugador WHERE id IN ({placeholders})", jugadores_ids)
    filas = cursor.fetchall()
    cursor.close()
    conn.close()
    return {fila[0] for fila in filas}


def obtener_todos():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM jugador ORDER BY nombre")
    filas = cursor.fetchall()
    cursor.close()
    conn.close()
    return [Jugador.from_row(f) for f in filas]


def obtener_por_id(jugador_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM jugador WHERE id = %s", (jugador_id,))
    fila = cursor.fetchone()
    cursor.close()
    conn.close()
    return Jugador.from_row(fila)


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


def actualizar_imagen(jugador_id, campo, path):
    """campo es 'imagen_vertical_path' o 'imagen_icono_path'. path puede
    ser None para borrar (volver al placeholder)."""
    if campo not in ("imagen_vertical_path", "imagen_icono_path"):
        raise ValueError(f"Campo de imagen inválido: {campo}")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE jugador SET {campo} = %s WHERE id = %s", (path, jugador_id))
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