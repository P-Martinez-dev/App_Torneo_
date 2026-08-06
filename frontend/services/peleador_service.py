from services.api_client import session as requests
from config import Config


class PeleadorInvalidoError(Exception):
    pass


class PeleadorConHistorialError(Exception):
    pass


class ImagenInvalidaError(Exception):
    pass


def listar_peleadores():
    resp = requests.get(f"{Config.API_BASE_URL}/peleadores")
    resp.raise_for_status()
    return resp.json()


def obtener_peleador(peleador_id):
    resp = requests.get(f"{Config.API_BASE_URL}/peleadores/{peleador_id}")
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def obtener_estadisticas(peleador_id):
    resp = requests.get(f"{Config.API_BASE_URL}/peleadores/{peleador_id}/estadisticas")
    resp.raise_for_status()
    return resp.json()


def obtener_navegacion(peleador_id):
    resp = requests.get(f"{Config.API_BASE_URL}/peleadores/{peleador_id}/navegacion")
    resp.raise_for_status()
    return resp.json()


def crear_peleador(nombre):
    resp = requests.post(f"{Config.API_BASE_URL}/peleadores", json={"nombre": nombre})
    if resp.status_code == 400:
        raise PeleadorInvalidoError(resp.json().get("error", "Datos inválidos"))
    resp.raise_for_status()
    return resp.json()


def actualizar_peleador(peleador_id, nombre):
    resp = requests.put(f"{Config.API_BASE_URL}/peleadores/{peleador_id}", json={"nombre": nombre})
    if resp.status_code == 400:
        raise PeleadorInvalidoError(resp.json().get("error", "Datos inválidos"))
    resp.raise_for_status()
    return resp.json()


def eliminar_peleador(peleador_id):
    resp = requests.delete(f"{Config.API_BASE_URL}/peleadores/{peleador_id}")
    if resp.status_code == 409:
        raise PeleadorConHistorialError(resp.json().get("error", "No se puede eliminar"))
    resp.raise_for_status()


def subir_icono(peleador_id, file_storage):
    archivos = {"imagen": (file_storage.filename, file_storage.stream, file_storage.mimetype)}
    resp = requests.post(f"{Config.API_BASE_URL}/peleadores/{peleador_id}/icono", files=archivos)
    if resp.status_code == 400:
        raise ImagenInvalidaError(resp.json().get("error", "Imagen inválida"))
    resp.raise_for_status()
    return resp.json()


def eliminar_icono(peleador_id):
    requests.delete(f"{Config.API_BASE_URL}/peleadores/{peleador_id}/icono").raise_for_status()
