from database.db import get_connection


# ---------- Creación ----------

def crear_muchos(partidos):
    if not partidos:
        return
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executemany(
        """INSERT INTO partido
           (torneo_id, jugador1_id, jugador2_id, fase, ronda, jornada, orden, estado)
           VALUES (%(torneo_id)s, %(jugador1_id)s, %(jugador2_id)s, %(fase)s,
                   %(ronda)s, %(jornada)s, %(orden)s, 'pendiente')""",
        partidos,
    )
    conn.commit()
    cursor.close()
    conn.close()


def crear_uno(partido):
    crear_muchos([partido])


# ---------- Consultas / navegación ----------

def obtener_por_id(partido_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM partido WHERE id = %s", (partido_id,))
    fila = cursor.fetchone()
    cursor.close()
    conn.close()
    return fila


def obtener_en_curso(torneo_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM partido WHERE torneo_id = %s AND estado = 'en_curso' LIMIT 1",
        (torneo_id,),
    )
    fila = cursor.fetchone()
    cursor.close()
    conn.close()
    return fila


def obtener_proximo_pendiente(torneo_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """SELECT * FROM partido
           WHERE torneo_id = %s AND estado = 'pendiente'
           ORDER BY orden ASC LIMIT 1""",
        (torneo_id,),
    )
    fila = cursor.fetchone()
    cursor.close()
    conn.close()
    return fila


def obtener_pendientes_y_pospuestos(torneo_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """SELECT * FROM partido
           WHERE torneo_id = %s AND estado IN ('pendiente', 'pospuesto')
           ORDER BY orden ASC""",
        (torneo_id,),
    )
    filas = cursor.fetchall()
    cursor.close()
    conn.close()
    return filas


def obtener_max_orden(torneo_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COALESCE(MAX(orden), 0) FROM partido WHERE torneo_id = %s", (torneo_id,))
    maximo = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return maximo


def contar_pendientes_por_fase(torneo_id, fase):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT COUNT(*) FROM partido
           WHERE torneo_id = %s AND fase = %s AND estado IN ('pendiente', 'en_curso', 'pospuesto')""",
        (torneo_id, fase),
    )
    total = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return total


# ---------- Cambios de estado ----------

def marcar_en_curso(partido_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE partido SET estado = 'en_curso' WHERE id = %s", (partido_id,))
    conn.commit()
    cursor.close()
    conn.close()


def marcar_pospuesto(partido_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT torneo_id, fase FROM partido WHERE id = %s", (partido_id,))
    partido = cursor.fetchone()

    cursor.execute(
        """SELECT COALESCE(MAX(orden), 0) AS max_orden FROM partido
           WHERE torneo_id = %s AND fase = %s""",
        (partido["torneo_id"], partido["fase"]),
    )
    nuevo_orden = cursor.fetchone()["max_orden"] + 1

    cursor.execute(
        "UPDATE partido SET estado = 'pospuesto', orden = %s WHERE id = %s",
        (nuevo_orden, partido_id),
    )
    conn.commit()
    cursor.close()
    conn.close()


def marcar_finalizado(partido_id, ganador_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE partido SET estado = 'finalizado', ganador_id = %s, fecha_jugado = NOW()
           WHERE id = %s""",
        (ganador_id, partido_id),
    )
    conn.commit()
    cursor.close()
    conn.close()


# ---------- Modo 5 vidas (trabajan sobre torneo_jugador_vidas) ----------

def descontar_vida(torneo_id, jugador_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """UPDATE torneo_jugador_vidas tjv
           JOIN torneo_jugador tj ON tj.id = tjv.torneo_jugador_id
           SET tjv.vidas = tjv.vidas - 1
           WHERE tj.torneo_id = %s AND tj.jugador_id = %s""",
        (torneo_id, jugador_id),
    )
    conn.commit()
    cursor.execute(
        """SELECT tjv.vidas FROM torneo_jugador_vidas tjv
           JOIN torneo_jugador tj ON tj.id = tjv.torneo_jugador_id
           WHERE tj.torneo_id = %s AND tj.jugador_id = %s""",
        (torneo_id, jugador_id),
    )
    vidas = cursor.fetchone()["vidas"]
    cursor.close()
    conn.close()
    return vidas


def marcar_eliminado(torneo_id, jugador_id):
    _actualizar_vidas(torneo_id, jugador_id, eliminado=True, en_cancha=False)


def marcar_en_cancha(torneo_id, jugador_id):
    _actualizar_vidas(torneo_id, jugador_id, en_cancha=True, posicion_cola=None)


def reencolar(torneo_id, jugador_id, nueva_posicion):
    _actualizar_vidas(torneo_id, jugador_id, en_cancha=False, posicion_cola=nueva_posicion)


def _actualizar_vidas(torneo_id, jugador_id, **campos):
    sets = ", ".join(f"tjv.{campo} = %s" for campo in campos)
    valores = list(campos.values()) + [torneo_id, jugador_id]
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"""UPDATE torneo_jugador_vidas tjv
            JOIN torneo_jugador tj ON tj.id = tjv.torneo_jugador_id
            SET {sets}
            WHERE tj.torneo_id = %s AND tj.jugador_id = %s""",
        valores,
    )
    conn.commit()
    cursor.close()
    conn.close()


def obtener_ultima_posicion_cola(torneo_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT COALESCE(MAX(tjv.posicion_cola), 0) FROM torneo_jugador_vidas tjv
           JOIN torneo_jugador tj ON tj.id = tjv.torneo_jugador_id
           WHERE tj.torneo_id = %s""",
        (torneo_id,),
    )
    maximo = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return maximo


def obtener_primero_en_cola(torneo_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """SELECT tj.jugador_id FROM torneo_jugador_vidas tjv
           JOIN torneo_jugador tj ON tj.id = tjv.torneo_jugador_id
           WHERE tj.torneo_id = %s AND tjv.eliminado = FALSE AND tjv.en_cancha = FALSE
           ORDER BY tjv.posicion_cola ASC LIMIT 1""",
        (torneo_id,),
    )
    fila = cursor.fetchone()
    cursor.close()
    conn.close()
    return fila


def contar_jugadores_activos(torneo_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT COUNT(*) FROM torneo_jugador_vidas tjv
           JOIN torneo_jugador tj ON tj.id = tjv.torneo_jugador_id
           WHERE tj.torneo_id = %s AND tjv.eliminado = FALSE""",
        (torneo_id,),
    )
    total = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return total

def obtener_ultima_ronda(torneo_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT COALESCE(MAX(ronda), 0) FROM partido
           WHERE torneo_id = %s AND fase = 'eliminacion'""",
        (torneo_id,),
    )
    ultima = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return ultima


def obtener_ganadores_ultima_ronda(torneo_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """SELECT ganador_id FROM partido
           WHERE torneo_id = %s AND fase = 'eliminacion'
             AND ronda = (SELECT MAX(ronda) FROM partido WHERE torneo_id = %s AND fase = 'eliminacion')
           ORDER BY orden ASC""",
        (torneo_id, torneo_id),
    )
    ganadores = [fila["ganador_id"] for fila in cursor.fetchall()]
    cursor.close()
    conn.close()
    return ganadores

def obtener_finalizados_por_grupo(grupo_id, excluidos_ids):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    placeholders = ",".join(["%s"] * len(excluidos_ids)) if excluidos_ids else None
    query = "SELECT * FROM partido WHERE grupo_id = %s AND estado = 'finalizado'"
    params = [grupo_id]
    if placeholders:
        query += f" AND id NOT IN ({placeholders})"
        params += excluidos_ids
    cursor.execute(query, params)
    filas = cursor.fetchall()
    cursor.close()
    conn.close()
    return filas


def obtener_finalizados_por_torneo(torneo_id, fase, excluidos_ids):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    placeholders = ",".join(["%s"] * len(excluidos_ids)) if excluidos_ids else None
    query = "SELECT * FROM partido WHERE torneo_id = %s AND fase = %s AND estado = 'finalizado'"
    params = [torneo_id, fase]
    if placeholders:
        query += f" AND id NOT IN ({placeholders})"
        params += excluidos_ids
    cursor.execute(query, params)
    filas = cursor.fetchall()
    cursor.close()
    conn.close()
    return filas