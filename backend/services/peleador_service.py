from mysql.connector import Error
from repositories import peleador_repository


class PeleadorNoEncontradoError(Exception):
    pass


class PeleadorConHistorialError(Exception):
    """Se lanza al intentar eliminar un peleador que ya fue usado en algún partido."""
    pass


def listar_peleadores():
    peleadores = peleador_repository.obtener_todos()
    return [p.to_dict() for p in peleadores]


def obtener_peleador(peleador_id):
    peleador = peleador_repository.obtener_por_id(peleador_id)
    if peleador is None:
        raise PeleadorNoEncontradoError(f"No existe el peleador {peleador_id}")
    return peleador.to_dict()


def crear_peleador(nombre):
    if not nombre or not nombre.strip():
        raise ValueError("El nombre del peleador es obligatorio")
    nuevo_id = peleador_repository.crear(nombre.strip())
    return obtener_peleador(nuevo_id)


def actualizar_peleador(peleador_id, nombre):
    if not nombre or not nombre.strip():
        raise ValueError("El nombre del peleador es obligatorio")
    actualizado = peleador_repository.actualizar(peleador_id, nombre.strip())
    if not actualizado:
        raise PeleadorNoEncontradoError(f"No existe el peleador {peleador_id}")
    return obtener_peleador(peleador_id)


def eliminar_peleador(peleador_id):
    try:
        eliminado = peleador_repository.eliminar(peleador_id)
    except Error as e:
        if e.errno == 1451:
            raise PeleadorConHistorialError(
                "No se puede eliminar un peleador que ya fue usado en algún partido"
            )
        raise
    if not eliminado:
        raise PeleadorNoEncontradoError(f"No existe el peleador {peleador_id}")