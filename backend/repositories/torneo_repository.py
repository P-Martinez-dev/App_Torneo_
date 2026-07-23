from database.db import get_connection
from models.torneo import Torneo


def crear(nombre, modo, fecha, cupos_eliminacion=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO torneo (nombre, modo, fecha, cupos_eliminacion, estado)
           VALUES (%s, %s, %s, %s, 'planificado')""",
        (nombre, modo, fecha, cupos_eliminacion),
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


def inicializar_cola_cinco_vidas(torneo_id, jugadores_ids_ordenados):
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
               VALUES (%s, 3, FALSE, %s, FALSE)""",
            (torneo_jugador_id, posicion),
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