from database.db import get_connection


def obtener_id(torneo_id, jugador_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM torneo_jugador WHERE torneo_id = %s AND jugador_id = %s",
        (torneo_id, jugador_id),
    )
    fila = cursor.fetchone()
    cursor.close()
    conn.close()
    return fila[0] if fila else None


def marcar_clasificado(torneo_jugador_id, clasificado, forzado=False, observacion=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE torneo_jugador_grupo
           SET clasificado = %s, clasificacion_forzada = %s, observacion_forzado = %s
           WHERE torneo_jugador_id = %s""",
        (clasificado, forzado, observacion, torneo_jugador_id),
    )
    conn.commit()
    cursor.close()
    conn.close()


def hay_pendientes(torneo_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT COUNT(*) FROM torneo_jugador_grupo tjg
           JOIN torneo_jugador tj ON tj.id = tjg.torneo_jugador_id
           WHERE tj.torneo_id = %s AND tjg.clasificado IS NULL""",
        (torneo_id,),
    )
    total = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return total > 0


def obtener_clasificados(torneo_id):
    """Devuelve [{jugador_id, grupo_id}] de todos los que clasificaron TRUE,
    tanto de grupos originales como de repechaje/desempate."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """SELECT tj.jugador_id, tjg.grupo_id FROM torneo_jugador_grupo tjg
           JOIN torneo_jugador tj ON tj.id = tjg.torneo_jugador_id
           WHERE tj.torneo_id = %s AND tjg.clasificado = TRUE""",
        (torneo_id,),
    )
    filas = cursor.fetchall()
    cursor.close()
    conn.close()
    return filas


def obtener_jugadores_de_grupo(grupo_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """SELECT tj.id AS torneo_jugador_id, j.id AS jugador_id, j.nombre
           FROM torneo_jugador_grupo tjg
           JOIN torneo_jugador tj ON tj.id = tjg.torneo_jugador_id
           JOIN jugador j ON j.id = tj.jugador_id
           WHERE tjg.grupo_id = %s""",
        (grupo_id,),
    )
    filas = cursor.fetchall()
    cursor.close()
    conn.close()
    return filas


def obtener_jugadores_de_torneo(torneo_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """SELECT tj.id AS torneo_jugador_id, j.id AS jugador_id, j.nombre
           FROM torneo_jugador tj
           JOIN jugador j ON j.id = tj.jugador_id
           WHERE tj.torneo_id = %s""",
        (torneo_id,),
    )
    filas = cursor.fetchall()
    cursor.close()
    conn.close()
    return filas


def obtener_grupo_original(torneo_id, jugador_id):
    """El grupo de tipo 'grupo' (no repechaje/desempate) al que pertenece el jugador."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """SELECT g.id, g.nombre FROM torneo_jugador_grupo tjg
           JOIN torneo_jugador tj ON tj.id = tjg.torneo_jugador_id
           JOIN grupo g ON g.id = tjg.grupo_id
           WHERE tj.torneo_id = %s AND tj.jugador_id = %s AND g.tipo = 'grupo'""",
        (torneo_id, jugador_id),
    )
    fila = cursor.fetchone()
    cursor.close()
    conn.close()
    return fila