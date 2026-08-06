from database.db import get_connection
from models.peleador import Peleador


def obtener_todos():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM peleador ORDER BY nombre")
    filas = cursor.fetchall()
    cursor.close()
    conn.close()
    return [Peleador.from_row(f) for f in filas]


def obtener_por_id(peleador_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM peleador WHERE id = %s", (peleador_id,))
    fila = cursor.fetchone()
    cursor.close()
    conn.close()
    return Peleador.from_row(fila)


def crear(nombre):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO peleador (nombre) VALUES (%s)", (nombre,))
    conn.commit()
    nuevo_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return nuevo_id


def actualizar(peleador_id, nombre):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE peleador SET nombre = %s WHERE id = %s", (nombre, peleador_id))
    conn.commit()
    filas_afectadas = cursor.rowcount
    cursor.close()
    conn.close()
    return filas_afectadas > 0


def eliminar(peleador_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM peleador WHERE id = %s", (peleador_id,))
    conn.commit()
    filas_afectadas = cursor.rowcount
    cursor.close()
    conn.close()
    return filas_afectadas > 0


def actualizar_imagen(peleador_id, path):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE peleador SET imagen_icono_path = %s WHERE id = %s", (path, peleador_id))
    conn.commit()
    cursor.close()
    conn.close()