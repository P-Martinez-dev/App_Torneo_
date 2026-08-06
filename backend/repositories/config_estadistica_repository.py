from database.db import get_connection


def obtener_ocultas():
    """El set de claves marcadas explícitamente como NO visibles. Todo lo
    que no aparezca acá se considera visible por defecto -- así no hace
    falta precargar una fila por cada estadística que existe."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT clave FROM config_estadistica WHERE visible = FALSE")
    claves = {fila[0] for fila in cursor.fetchall()}
    cursor.close()
    conn.close()
    return claves


def actualizar_visibilidad(clave, visible):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO config_estadistica (clave, visible) VALUES (%s, %s)
           ON DUPLICATE KEY UPDATE visible = %s""",
        (clave, visible, visible),
    )
    conn.commit()
    cursor.close()
    conn.close()
