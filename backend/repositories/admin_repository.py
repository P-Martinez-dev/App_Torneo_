from database.db import get_connection
from models.admin_usuario import AdminUsuario


def obtener_por_usuario(usuario):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM admin_usuario WHERE usuario = %s", (usuario,))
    fila = cursor.fetchone()
    cursor.close()
    conn.close()
    return AdminUsuario.from_row(fila)


def obtener_todos():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM admin_usuario ORDER BY usuario")
    filas = cursor.fetchall()
    cursor.close()
    conn.close()
    return [AdminUsuario.from_row(f) for f in filas]


def contar():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM admin_usuario")
    total = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return total


def crear(usuario, password_hash):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO admin_usuario (usuario, password_hash) VALUES (%s, %s)",
        (usuario, password_hash),
    )
    conn.commit()
    nuevo_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return nuevo_id


def eliminar(admin_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM admin_usuario WHERE id = %s", (admin_id,))
    conn.commit()
    filas_afectadas = cursor.rowcount
    cursor.close()
    conn.close()
    return filas_afectadas > 0
