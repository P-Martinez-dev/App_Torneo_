from database.db import get_connection
from models.partido import Partido


# =========================================================
# Creación
# =========================================================

def crear_muchos(partidos):
    if not partidos:
        return
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executemany(
        """INSERT INTO partido
           (torneo_id, jugador1_id, jugador2_id, fase, ronda, jornada, orden, grupo_id, estado)
           VALUES (%(torneo_id)s, %(jugador1_id)s, %(jugador2_id)s, %(fase)s,
                   %(ronda)s, %(jornada)s, %(orden)s, %(grupo_id)s, 'pendiente')""",
        partidos,
    )
    conn.commit()
    cursor.close()
    conn.close()


def crear_uno(partido):
    crear_muchos([partido])


# =========================================================
# Consultas / navegación
# =========================================================

def obtener_por_id(partido_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM partido WHERE id = %s", (partido_id,))
    fila = cursor.fetchone()
    cursor.close()
    conn.close()
    return Partido.from_row(fila)


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
    return Partido.from_row(fila)


def obtener_proximo_pendiente(torneo_id):
    """
    Prioriza 'pendiente' sobre 'pospuesto' (para eso existe posponer: bajarle
    la prioridad a un partido puntual) -- pero si no queda NINGÚN pendiente
    normal, sí hay que volver a ofrecer los pospuestos, o el torneo se queda
    trabado con un partido que nadie vuelve a ver.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """SELECT * FROM partido
           WHERE torneo_id = %s AND estado IN ('pendiente', 'pospuesto')
           ORDER BY (estado = 'pendiente') DESC, orden ASC
           LIMIT 1""",
        (torneo_id,),
    )
    fila = cursor.fetchone()
    cursor.close()
    conn.close()
    return Partido.from_row(fila)


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
    return [Partido.from_row(f) for f in filas]


def obtener_por_torneo(torneo_id):
    """Todos los partidos del torneo, sin filtrar por estado. Sirve para
    inspeccionar cualquier fase/ronda (ej: ver los cuartos de final)."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM partido WHERE torneo_id = %s ORDER BY orden ASC", (torneo_id,)
    )
    filas = cursor.fetchall()
    cursor.close()
    conn.close()
    return [Partido.from_row(f) for f in filas]


def obtener_max_orden(torneo_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COALESCE(MAX(orden), 0) FROM partido WHERE torneo_id = %s", (torneo_id,)
    )
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


def contar_pendientes_por_grupo(grupo_id):
    """A diferencia de contar_pendientes_por_fase (que mira todo el torneo),
    esto scopea a una instancia puntual de grupo -- necesario para no pisar
    la resolución de un desempate/repechaje cuando hay varios corriendo en
    paralelo en distintos grupos."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT COUNT(*) FROM partido
           WHERE grupo_id = %s AND estado IN ('pendiente', 'en_curso', 'pospuesto')""",
        (grupo_id,),
    )
    total = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return total


def obtener_finalizados_por_grupo(grupo_id, excluidos_ids):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM partido WHERE grupo_id = %s AND estado = 'finalizado'"
    params = [grupo_id]
    if excluidos_ids:
        placeholders = ",".join(["%s"] * len(excluidos_ids))
        query += f" AND id NOT IN ({placeholders})"
        params += excluidos_ids
    cursor.execute(query, params)
    filas = cursor.fetchall()
    cursor.close()
    conn.close()
    return [Partido.from_row(f) for f in filas]


def obtener_por_fase_y_ronda(torneo_id, fase, ronda):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM partido WHERE torneo_id = %s AND fase = %s AND ronda = %s ORDER BY orden",
        (torneo_id, fase, ronda),
    )
    filas = cursor.fetchall()
    cursor.close()
    conn.close()
    return [Partido.from_row(f) for f in filas]


def reemplazar_partidos(ids_a_eliminar, nuevos_partidos):
    """
    Borra ids_a_eliminar y crea nuevos_partidos en UNA sola transacción --
    si algo falla en el medio (se cae la conexión, etc.), hace rollback y
    no queda a mitad de camino (ni los viejos borrados sin los nuevos
    puestos, ni duplicados). Pensado para resembrar_bracket_manual.
    """
    conn = get_connection()
    # Varias escrituras que tienen que aplicarse todas o ninguna: como la
    # conexion viene en autocommit (para que las LECTURAS no paguen el costo
    # de abrir y cerrar una transaccion en cada una), acá se abre uno
    # explicito para no perder esa garantia.
    conn.start_transaction()
    cursor = conn.cursor()
    try:
        if ids_a_eliminar:
            placeholders = ",".join(["%s"] * len(ids_a_eliminar))
            cursor.execute(f"DELETE FROM partido WHERE id IN ({placeholders})", ids_a_eliminar)

        if nuevos_partidos:
            cursor.executemany(
                """INSERT INTO partido
                   (torneo_id, jugador1_id, jugador2_id, fase, ronda, jornada, orden, grupo_id, estado)
                   VALUES (%(torneo_id)s, %(jugador1_id)s, %(jugador2_id)s, %(fase)s,
                           %(ronda)s, %(jornada)s, %(orden)s, %(grupo_id)s, 'pendiente')""",
                nuevos_partidos,
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def eliminar(partido_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM partido WHERE id = %s", (partido_id,))
    conn.commit()
    cursor.close()
    conn.close()


def obtener_finalizados_por_torneo(torneo_id, fase, excluidos_ids):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM partido WHERE torneo_id = %s AND fase = %s AND estado = 'finalizado'"
    params = [torneo_id, fase]
    if excluidos_ids:
        placeholders = ",".join(["%s"] * len(excluidos_ids))
        query += f" AND id NOT IN ({placeholders})"
        params += excluidos_ids
    cursor.execute(query, params)
    filas = cursor.fetchall()
    cursor.close()
    conn.close()
    return [Partido.from_row(f) for f in filas]


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


def obtener_partido_eliminacion(torneo_id, jugador_id):
    """El partido (cinco_vidas) en el que un jugador perdió su última vida
    en ese torneo específico -- o None si nunca fue eliminado ahí (fue
    campeón, o el torneo sigue en curso)."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """SELECT * FROM partido
           WHERE torneo_id = %s AND fase = 'cinco_vidas' AND estado = 'finalizado'
             AND (jugador1_id = %s OR jugador2_id = %s) AND ganador_id != %s
           ORDER BY fecha_jugado DESC LIMIT 1""",
        (torneo_id, jugador_id, jugador_id, jugador_id),
    )
    fila = cursor.fetchone()
    cursor.close()
    conn.close()
    return Partido.from_row(fila)


def obtener_finalizados_por_jugador(jugador_id):
    """Todos los partidos finalizados de un jugador en cualquier torneo,
    ordenados cronológicamente. Excluye repechaje/desempate a propósito
    (mismo criterio que las estadísticas de la tabla general: no son
    partidos 'de verdad' del torneo).

    Importante: se ordena por la FECHA DEL TORNEO (torneo.fecha) + el
    'orden' interno del partido, no por partido.fecha_jugado -- esa
    columna guarda el momento en que se CARGÓ el resultado, no cuándo
    pasó de verdad. Si reconstruís un torneo viejo, fecha_jugado queda en
    'ahora', y ordenar por eso invierte la cronología real entre torneos
    reconstruidos en distinto orden al que pasaron en la vida real."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """SELECT p.* FROM partido p
           JOIN torneo t ON t.id = p.torneo_id
           WHERE (p.jugador1_id = %s OR p.jugador2_id = %s)
             AND p.estado = 'finalizado' AND p.fase NOT IN ('repechaje', 'desempate')
           ORDER BY t.fecha ASC, p.orden ASC""",
        (jugador_id, jugador_id),
    )
    filas = cursor.fetchall()
    cursor.close()
    conn.close()
    return [Partido.from_row(f) for f in filas]


def obtener_finalizados_por_torneos(torneos_ids):
    """Partidos finalizados de una lista de torneos, para el desempate de la
    tabla general (puntos de victoria y win rate). Excluye repechaje y
    desempate a propósito: son mecanismos de resolución de empates, no
    partidos "de verdad" del torneo, y no deben inflar el récord de nadie.
    Eliminación y tercer puesto sí cuentan."""
    if not torneos_ids:
        return []
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    placeholders = ",".join(["%s"] * len(torneos_ids))
    cursor.execute(
        f"""SELECT * FROM partido WHERE torneo_id IN ({placeholders})
            AND estado = 'finalizado' AND fase NOT IN ('repechaje', 'desempate')""",
        torneos_ids,
    )
    filas = cursor.fetchall()
    cursor.close()
    conn.close()
    return [Partido.from_row(f) for f in filas]


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


def obtener_perdedores_ultima_ronda(torneo_id):
    """Los dos que pierden semifinal, para armar el partido por el tercer puesto."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """SELECT jugador1_id, jugador2_id, ganador_id FROM partido
           WHERE torneo_id = %s AND fase = 'eliminacion'
             AND ronda = (SELECT MAX(ronda) FROM partido WHERE torneo_id = %s AND fase = 'eliminacion')
           ORDER BY orden ASC""",
        (torneo_id, torneo_id),
    )
    filas = cursor.fetchall()
    cursor.close()
    conn.close()
    perdedores = []
    for f in filas:
        perdedor = f["jugador2_id"] if f["ganador_id"] == f["jugador1_id"] else f["jugador1_id"]
        perdedores.append(perdedor)
    return perdedores


# =========================================================
# Cambios de estado
# =========================================================

def marcar_en_curso(partido_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE partido SET estado = 'en_curso' WHERE id = %s", (partido_id,))
    conn.commit()
    cursor.close()
    conn.close()


def marcar_pospuesto(partido_id):
    conn = get_connection()
    # Varias escrituras que tienen que aplicarse todas o ninguna: como la
    # conexion viene en autocommit (para que las LECTURAS no paguen el costo
    # de abrir y cerrar una transaccion en cada una), acá se abre uno
    # explicito para no perder esa garantia.
    conn.start_transaction()
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


def marcar_finalizado(partido_id, ganador_id, peleador1_id=None, peleador2_id=None, rondas_jugadas=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE partido SET estado = 'finalizado', ganador_id = %s,
           jugador1_peleador_id = %s, jugador2_peleador_id = %s, rondas_jugadas = %s,
           fecha_jugado = NOW()
           WHERE id = %s""",
        (ganador_id, peleador1_id, peleador2_id, rondas_jugadas, partido_id),
    )
    conn.commit()
    cursor.close()
    conn.close()


def actualizar_resultado(partido_id, ganador_id, peleador1_id=None, peleador2_id=None, rondas_jugadas=None):
    """A diferencia de marcar_finalizado, esto es para CORREGIR un partido
    que ya estaba finalizado -- no toca estado ni fecha_jugado (no es un
    'se jugó ahora', es 'se corrigió lo que ya se había cargado')."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE partido SET ganador_id = %s, jugador1_peleador_id = %s,
           jugador2_peleador_id = %s, rondas_jugadas = %s
           WHERE id = %s""",
        (ganador_id, peleador1_id, peleador2_id, rondas_jugadas, partido_id),
    )
    conn.commit()
    cursor.close()
    conn.close()


def marcar_no_realizado(partido_id):
    """Partido que no se va a jugar (no confundir con 'pospuesto', que
    implica que se retoma después). No cuenta en tablas (obtener_finalizados_*
    ya filtra por estado='finalizado') ni bloquea el avance de fase
    (contar_pendientes_por_fase/grupo ya no lo incluye en su IN, porque no
    es 'pendiente', 'en_curso' ni 'pospuesto')."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE partido SET estado = 'no_realizado' WHERE id = %s", (partido_id,)
    )
    conn.commit()
    cursor.close()
    conn.close()


# =========================================================
# Modo 5 vidas (trabajan sobre torneo_jugador_vidas)
# =========================================================

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
    siguiente_orden = _obtener_siguiente_orden_eliminacion(torneo_id)
    _actualizar_vidas(torneo_id, jugador_id, eliminado=True, en_cancha=False,
                       orden_eliminacion=siguiente_orden)


def _obtener_siguiente_orden_eliminacion(torneo_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT COALESCE(MAX(tjv.orden_eliminacion), 0) FROM torneo_jugador_vidas tjv
           JOIN torneo_jugador tj ON tj.id = tjv.torneo_jugador_id
           WHERE tj.torneo_id = %s""",
        (torneo_id,),
    )
    maximo = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return maximo + 1


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

def obtener_partidos_cinco_vidas_de_torneos(torneos_ids):
    """Todos los partidos cinco_vidas finalizados de VARIOS torneos, en una
    sola consulta -- devuelve {torneo_id: [partidos]}.

    Reemplaza a pedir obtener_partido_eliminacion() una vez por cada
    jugador de cada torneo: con esto se trae todo junto y el "quién eliminó
    a quién" se resuelve en memoria."""
    if not torneos_ids:
        return {}
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    placeholders = ",".join(["%s"] * len(torneos_ids))
    cursor.execute(
        f"""SELECT * FROM partido
            WHERE torneo_id IN ({placeholders})
              AND fase = 'cinco_vidas' AND estado = 'finalizado'""",
        torneos_ids,
    )
    filas = cursor.fetchall()
    cursor.close()
    conn.close()

    por_torneo = {torneo_id: [] for torneo_id in torneos_ids}
    for fila in filas:
        por_torneo[fila["torneo_id"]].append(Partido.from_row(fila))
    return por_torneo