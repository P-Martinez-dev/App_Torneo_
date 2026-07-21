from mysql.connector import Error
from repositories import jugador_repository
from models.jugador import Jugador


class JugadorNoEncontradoError(Exception):
    pass


class JugadorConHistorialError(Exception):
    """Se lanza al intentar eliminar un jugador que ya participó de partidos/torneos."""
    pass


def listar_jugadores():
    filas = jugador_repository.obtener_todos()
    return [Jugador.from_row(f).to_dict() for f in filas]


def obtener_jugador(jugador_id):
    fila = jugador_repository.obtener_por_id(jugador_id)
    if fila is None:
        raise JugadorNoEncontradoError(f"No existe el jugador {jugador_id}")
    return Jugador.from_row(fila).to_dict()


def crear_jugador(nombre, fecha_nacimiento=None):
    if not nombre or not nombre.strip():
        raise ValueError("El nombre del jugador es obligatorio")
    nuevo_id = jugador_repository.crear(nombre.strip(), fecha_nacimiento)
    return obtener_jugador(nuevo_id)


def actualizar_jugador(jugador_id, nombre, fecha_nacimiento=None):
    if not nombre or not nombre.strip():
        raise ValueError("El nombre del jugador es obligatorio")
    actualizado = jugador_repository.actualizar(jugador_id, nombre.strip(), fecha_nacimiento)
    if not actualizado:
        raise JugadorNoEncontradoError(f"No existe el jugador {jugador_id}")
    return obtener_jugador(jugador_id)


def eliminar_jugador(jugador_id):
    try:
        eliminado = jugador_repository.eliminar(jugador_id)
    except Error as e:
        # error 1451 = "Cannot delete or update a parent row: a foreign key constraint fails"
        if e.errno == 1451:
            raise JugadorConHistorialError(
                "No se puede eliminar un jugador que ya participó en torneos o partidos"
            )
        raise
    if not eliminado:
        raise JugadorNoEncontradoError(f"No existe el jugador {jugador_id}")