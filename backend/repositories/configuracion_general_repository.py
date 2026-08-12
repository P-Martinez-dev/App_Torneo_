from database.db import get_connection

CAMPOS = (
    "fecha_proximo_torneo, descripcion_inicio, descripcion_tablas, nombre_club, "
    "mostrar_tile_tablas, mostrar_tile_torneos, mostrar_tile_jugadores, mostrar_tile_peleadores, "
    "info_tablas, info_formatos"
)


def obtener():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"SELECT {CAMPOS} FROM configuracion_general WHERE id = 1")
    fila = cursor.fetchone()
    cursor.close()
    conn.close()
    return fila or {
        "fecha_proximo_torneo": None, "descripcion_inicio": None, "descripcion_tablas": None,
        "nombre_club": None, "mostrar_tile_tablas": True, "mostrar_tile_torneos": True,
        "mostrar_tile_jugadores": True, "mostrar_tile_peleadores": True,
        "info_tablas": None, "info_formatos": None,
    }


def obtener_fecha_proximo_torneo():
    return obtener()["fecha_proximo_torneo"]


def obtener_nombre_club():
    return obtener()["nombre_club"]


def actualizar_fecha_proximo_torneo(fecha):
    _actualizar_campo("fecha_proximo_torneo", fecha)


def actualizar_descripcion_inicio(descripcion):
    _actualizar_campo("descripcion_inicio", descripcion)


def actualizar_descripcion_tablas(descripcion):
    _actualizar_campo("descripcion_tablas", descripcion)


def actualizar_nombre_club(nombre):
    _actualizar_campo("nombre_club", nombre)


def actualizar_info_tablas(texto):
    _actualizar_campo("info_tablas", texto)


def actualizar_info_formatos(texto):
    _actualizar_campo("info_formatos", texto)


CAMPOS_TILE_VALIDOS = {
    "tablas": "mostrar_tile_tablas",
    "torneos": "mostrar_tile_torneos",
    "jugadores": "mostrar_tile_jugadores",
    "peleadores": "mostrar_tile_peleadores",
}


def actualizar_tile(nombre_tile, visible):
    if nombre_tile not in CAMPOS_TILE_VALIDOS:
        raise ValueError(f"'{nombre_tile}' no es un tile conocido")
    _actualizar_campo(CAMPOS_TILE_VALIDOS[nombre_tile], visible)


def _actualizar_campo(campo, valor):
    """Los nombres de columna nunca vienen del usuario (son literales
    fijos definidos acá mismo), así que armar la query con el nombre de
    columna interpolado es seguro -- el VALOR sigue yendo parametrizado."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE configuracion_general SET {campo} = %s WHERE id = 1", (valor,))
    conn.commit()
    cursor.close()
    conn.close()
