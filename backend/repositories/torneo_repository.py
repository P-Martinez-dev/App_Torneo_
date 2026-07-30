from database.db import get_connection
from models.torneo import Torneo


def crear(nombre, modo, fecha, cupos_eliminacion=None, vidas_iniciales=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO torneo (nombre, modo, fecha, cupos_eliminacion, vidas_iniciales, estado)
           VALUES (%s, %s, %s, %s, %s, 'planificado')""",
        (nombre, modo, fecha, cupos_eliminacion, vidas_iniciales),
    )
    conn.commit()
    nuevo_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return nuevo_id


def obtener_por_id(torneo_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM torneo WHERE id = %s", (torneo_id,))
    fila = cursor.fetchone()
    cursor.close()
    conn.close()
    return Torneo.from_row(fila)


def obtener_todos():
    """Listado de torneos, más recientes primero (por fecha del evento,
    no por id -- alguien puede cargar torneos pasados fuera de orden)."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM torneo ORDER BY fecha DESC, id DESC")
    filas = cursor.fetchall()
    cursor.close()
    conn.close()
    return [Torneo.from_row(f) for f in filas]


def asignar_jugadores(torneo_id, jugadores_ids):
    """Crea las filas base en torneo_jugador. Devuelve dict {jugador_id: torneo_jugador_id}."""
    conn = get_connection()
    cursor = conn.cursor()
    ids_map = {}
    for jugador_id in jugadores_ids:
        cursor.execute(
            "INSERT INTO torneo_jugador (torneo_id, jugador_id) VALUES (%s, %s)",
            (torneo_id, jugador_id),
        )
        ids_map[jugador_id] = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    return ids_map


def asignar_jugadores_a_grupo(grupo_id, jugadores_ids):
    """Inserta en torneo_jugador_grupo para jugadores ya existentes en torneo_jugador."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    for jugador_id in jugadores_ids:
        cursor.execute(
            """SELECT tj.id FROM torneo_jugador tj
               JOIN grupo g ON g.torneo_id = tj.torneo_id
               WHERE g.id = %s AND tj.jugador_id = %s""",
            (grupo_id, jugador_id),
        )
        fila = cursor.fetchone()
        cursor.execute(
            """INSERT INTO torneo_jugador_grupo (torneo_jugador_id, grupo_id)
               VALUES (%s, %s)""",
            (fila["id"], grupo_id),
        )
    conn.commit()
    cursor.close()
    conn.close()


def inicializar_cola_cinco_vidas(torneo_id, jugadores_ids_ordenados, vidas_iniciales):
    """
    Crea solo la extensión torneo_jugador_vidas. Las filas base de
    torneo_jugador ya existen (las crea asignar_jugadores en crear_torneo).
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    for posicion, jugador_id in enumerate(jugadores_ids_ordenados):
        cursor.execute(
            "SELECT id FROM torneo_jugador WHERE torneo_id = %s AND jugador_id = %s",
            (torneo_id, jugador_id),
        )
        torneo_jugador_id = cursor.fetchone()["id"]
        # los dos primeros arrancan jugando: no están "en cola" en el sentido
        # estricto, pero posicion_cola igual les sirve de referencia inicial
        cursor.execute(
            """INSERT INTO torneo_jugador_vidas
               (torneo_jugador_id, vidas, eliminado, posicion_cola, en_cancha)
               VALUES (%s, %s, FALSE, %s, FALSE)""",
            (torneo_jugador_id, vidas_iniciales, posicion),
        )
    conn.commit()
    cursor.close()
    conn.close()


def marcar_finalizado(torneo_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE torneo SET estado = 'finalizado' WHERE id = %s", (torneo_id,))
    conn.commit()
    cursor.close()
    conn.close()


def marcar_en_curso(torneo_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE torneo SET estado = 'en_curso' WHERE id = %s", (torneo_id,))
    conn.commit()
    cursor.close()
    conn.close()


def obtener_finalizados(excluidos_ids=None):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM torneo WHERE estado = 'finalizado'"
    params = []
    if excluidos_ids:
        placeholders = ",".join(["%s"] * len(excluidos_ids))
        query += f" AND id NOT IN ({placeholders})"
        params += excluidos_ids
    cursor.execute(query, params)
    filas = cursor.fetchall()
    cursor.close()
    conn.close()
    return [Torneo.from_row(f) for f in filas]


def obtener_finalizados_de_jugador(jugador_id):
    """Torneos finalizados donde participó un jugador -- para calcular su
    mejor puesto histórico, veces campeón, etc."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """SELECT t.* FROM torneo t
           JOIN torneo_jugador tj ON tj.torneo_id = t.id
           WHERE tj.jugador_id = %s AND t.estado = 'finalizado'""",
        (jugador_id,),
    )
    filas = cursor.fetchall()
    cursor.close()
    conn.close()
    return [Torneo.from_row(f) for f in filas]


def obtener_todos_de_jugador(jugador_id):
    """Todos los torneos donde participó un jugador, sin importar el estado
    (para contar cuántos jugó por modo, incluidos los que siguen en curso)."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """SELECT t.* FROM torneo t
           JOIN torneo_jugador tj ON tj.torneo_id = t.id
           WHERE tj.jugador_id = %s""",
        (jugador_id,),
    )
    filas = cursor.fetchall()
    cursor.close()
    conn.close()
    return [Torneo.from_row(f) for f in filas]


def eliminar_completo(torneo_id):
    """
    Borra el torneo y todo lo que depende de él, en el orden correcto
    para no chocar con las foreign keys: primero lo más 'hijo'
    (partido, extensiones de torneo_jugador), después grupo y
    torneo_jugador, y recién al final el torneo en sí.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM partido WHERE torneo_id = %s", (torneo_id,))
        cursor.execute(
            """DELETE tjg FROM torneo_jugador_grupo tjg
               JOIN torneo_jugador tj ON tj.id = tjg.torneo_jugador_id
               WHERE tj.torneo_id = %s""",
            (torneo_id,),
        )
        cursor.execute(
            """DELETE tjv FROM torneo_jugador_vidas tjv
               JOIN torneo_jugador tj ON tj.id = tjv.torneo_jugador_id
               WHERE tj.torneo_id = %s""",
            (torneo_id,),
        )
        cursor.execute("DELETE FROM grupo WHERE torneo_id = %s", (torneo_id,))
        cursor.execute("DELETE FROM torneo_jugador WHERE torneo_id = %s", (torneo_id,))
        cursor.execute("DELETE FROM torneo WHERE id = %s", (torneo_id,))
        filas_afectadas = cursor.rowcount
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
    return filas_afectadas > 0