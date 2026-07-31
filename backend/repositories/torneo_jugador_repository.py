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


def marcar_clasificado(torneo_jugador_id, grupo_id, clasificado, forzado=False, observacion=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE torneo_jugador_grupo
           SET clasificado = %s, clasificacion_forzada = %s, observacion_forzado = %s
           WHERE torneo_jugador_id = %s AND grupo_id = %s""",
        (clasificado, forzado, observacion, torneo_jugador_id, grupo_id),
    )
    conn.commit()
    cursor.close()
    conn.close()


def obtener_grupo_pendiente(torneo_jugador_id):
    """El grupo (de los que pertenece este torneo_jugador) donde todavía
    no se definió si clasificó o no. Se usa para saber a cuál aplicar
    un forzado cuando no se especifica el grupo explícitamente."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT grupo_id FROM torneo_jugador_grupo
           WHERE torneo_jugador_id = %s AND clasificado IS NULL LIMIT 1""",
        (torneo_jugador_id,),
    )
    fila = cursor.fetchone()
    cursor.close()
    conn.close()
    return fila[0] if fila else None


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


def hay_pendientes_en_grupo(grupo_id):
    """Igual que hay_pendientes pero scopeado a un grupo puntual -- se usa
    para detectar el grupo específico que quedó trabado en un empate sin
    resolver (todos sus partidos terminados, pero nadie quedó marcado
    clasificado True/False)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM torneo_jugador_grupo WHERE grupo_id = %s AND clasificado IS NULL",
        (grupo_id,),
    )
    total = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return total > 0


def hay_desempates_internos_pendientes(torneo_id):
    """Igual que hay_pendientes, pero scopeado solo a los mini-grupos de
    desempate interno de grupo (grupo_padre_id IS NOT NULL). Se usa para
    saber cuándo ya se puede calcular el repechaje cruzado entre grupos."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT COUNT(*) FROM torneo_jugador_grupo tjg
           JOIN grupo g ON g.id = tjg.grupo_id
           WHERE g.torneo_id = %s AND g.grupo_padre_id IS NOT NULL
             AND tjg.clasificado IS NULL""",
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


def contar_repechajes_y_desempates(jugador_id):
    """Cantidad de veces (grupos distintos, no partidos) que un jugador
    terminó en un repechaje o desempate a lo largo de su carrera."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT COUNT(DISTINCT g.id) FROM torneo_jugador_grupo tjg
           JOIN torneo_jugador tj ON tj.id = tjg.torneo_jugador_id
           JOIN grupo g ON g.id = tjg.grupo_id
           WHERE tj.jugador_id = %s AND g.tipo IN ('repechaje', 'desempate')""",
        (jugador_id,),
    )
    total = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return total


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


def obtener_vidas_de_torneo(torneo_id):
    """Estado de vidas de todos los jugadores de un torneo modo 'cinco_vidas'."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """SELECT tj.jugador_id, tjv.eliminado, tjv.orden_eliminacion
           FROM torneo_jugador_vidas tjv
           JOIN torneo_jugador tj ON tj.id = tjv.torneo_jugador_id
           WHERE tj.torneo_id = %s""",
        (torneo_id,),
    )
    filas = cursor.fetchall()
    cursor.close()
    conn.close()
    return filas