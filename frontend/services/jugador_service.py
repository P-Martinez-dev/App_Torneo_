import requests
from config import Config


class JugadorInvalidoError(Exception):
    pass


class JugadorConHistorialError(Exception):
    pass


class ImagenInvalidaError(Exception):
    pass


def listar_jugadores():
    resp = requests.get(f"{Config.API_BASE_URL}/jugadores")
    resp.raise_for_status()
    return resp.json()


def obtener_jugador(jugador_id):
    resp = requests.get(f"{Config.API_BASE_URL}/jugadores/{jugador_id}")
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def crear_jugador(nombre, fecha_nacimiento=None):
    resp = requests.post(
        f"{Config.API_BASE_URL}/jugadores",
        json={"nombre": nombre, "fecha_nacimiento": fecha_nacimiento or None},
    )
    if resp.status_code == 400:
        raise JugadorInvalidoError(resp.json().get("error", "Datos inválidos"))
    resp.raise_for_status()
    return resp.json()


def actualizar_jugador(jugador_id, nombre, fecha_nacimiento=None):
    resp = requests.put(
        f"{Config.API_BASE_URL}/jugadores/{jugador_id}",
        json={"nombre": nombre, "fecha_nacimiento": fecha_nacimiento or None},
    )
    if resp.status_code == 400:
        raise JugadorInvalidoError(resp.json().get("error", "Datos inválidos"))
    resp.raise_for_status()
    return resp.json()


def eliminar_jugador(jugador_id):
    resp = requests.delete(f"{Config.API_BASE_URL}/jugadores/{jugador_id}")
    if resp.status_code == 409:
        raise JugadorConHistorialError(resp.json().get("error", "No se puede eliminar"))
    resp.raise_for_status()


def subir_imagen_vertical(jugador_id, file_storage):
    return _subir_imagen(jugador_id, "imagen-vertical", file_storage)


def subir_icono(jugador_id, file_storage):
    return _subir_imagen(jugador_id, "icono", file_storage)


def eliminar_imagen_vertical(jugador_id):
    requests.delete(f"{Config.API_BASE_URL}/jugadores/{jugador_id}/imagen-vertical").raise_for_status()


def eliminar_icono(jugador_id):
    requests.delete(f"{Config.API_BASE_URL}/jugadores/{jugador_id}/icono").raise_for_status()


def _subir_imagen(jugador_id, ruta, file_storage):
    archivos = {"imagen": (file_storage.filename, file_storage.stream, file_storage.mimetype)}
    resp = requests.post(f"{Config.API_BASE_URL}/jugadores/{jugador_id}/{ruta}", files=archivos)
    if resp.status_code == 400:
        raise ImagenInvalidaError(resp.json().get("error", "Imagen inválida"))
    resp.raise_for_status()
    return resp.json()
