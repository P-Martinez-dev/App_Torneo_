import time

from services.api_client import session as requests
from config import Config


class PeleadorInvalidoError(Exception):
    pass


class PeleadorConHistorialError(Exception):
    pass


class ImagenInvalidaError(Exception):
    pass


# El listado se usa varias veces DENTRO de un mismo pedido (para sacar la
# entidad puntual y para las flechas de navegación). Se guarda unos segundos
# para no repetir el viaje al backend en ese lapso -- el backend igual lo
# tiene cacheado, pero el viaje en sí también cuesta.
_SEGUNDOS_CACHE_LISTADO = 5
_cache_listado = {"valor": None, "vence_en": 0}


def listar_peleadores():
    if _cache_listado["valor"] is not None and time.time() < _cache_listado["vence_en"]:
        return _cache_listado["valor"]
    resp = requests.get(f"{Config.API_BASE_URL}/peleadores")
    resp.raise_for_status()
    datos = resp.json()
    _cache_listado["valor"] = datos
    _cache_listado["vence_en"] = time.time() + _SEGUNDOS_CACHE_LISTADO
    return datos


def _invalidar_cache_listado():
    _cache_listado["valor"] = None
    _cache_listado["vence_en"] = 0


def obtener_peleador(peleador_id):
    """Sale del listado que el backend ya tiene cacheado, en vez de un
    pedido puntual: es exactamente la misma información y ahorra un viaje
    entero, que contra una base remota es lo que más se nota."""
    for x in listar_peleadores():
        if x["id"] == peleador_id:
            return x
    return None


def obtener_estadisticas(peleador_id):
    resp = requests.get(f"{Config.API_BASE_URL}/peleadores/{peleador_id}/estadisticas")
    resp.raise_for_status()
    return resp.json()


def obtener_navegacion(peleador_id):
    """Las flechas de anterior/siguiente salen del listado que ya se pide
    igual (y que el backend tiene cacheado), en vez de un pedido aparte:
    es la misma info, y cada viaje al backend cuesta caro contra una base
    remota."""
    todos = listar_peleadores()
    ids = [x["id"] for x in todos]
    if peleador_id not in ids:
        return {"anterior_id": None, "siguiente_id": None}
    idx = ids.index(peleador_id)
    return {
        "anterior_id": ids[idx - 1] if idx > 0 else None,
        "siguiente_id": ids[idx + 1] if idx < len(ids) - 1 else None,
    }


def crear_peleador(nombre):
    resp = requests.post(f"{Config.API_BASE_URL}/peleadores", json={"nombre": nombre})
    if resp.status_code == 400:
        raise PeleadorInvalidoError(resp.json().get("error", "Datos inválidos"))
    resp.raise_for_status()
    _invalidar_cache_listado()  # que el cambio se vea ya, sin esperar al cache
    return resp.json()


def actualizar_peleador(peleador_id, nombre):
    resp = requests.put(f"{Config.API_BASE_URL}/peleadores/{peleador_id}", json={"nombre": nombre})
    if resp.status_code == 400:
        raise PeleadorInvalidoError(resp.json().get("error", "Datos inválidos"))
    resp.raise_for_status()
    _invalidar_cache_listado()  # que el cambio se vea ya, sin esperar al cache
    return resp.json()


def eliminar_peleador(peleador_id):
    resp = requests.delete(f"{Config.API_BASE_URL}/peleadores/{peleador_id}")
    if resp.status_code == 409:
        raise PeleadorConHistorialError(resp.json().get("error", "No se puede eliminar"))
    resp.raise_for_status()
    _invalidar_cache_listado()  # que el cambio se vea ya, sin esperar al cache


def subir_icono(peleador_id, file_storage):
    archivos = {"imagen": (file_storage.filename, file_storage.stream, file_storage.mimetype)}
    resp = requests.post(f"{Config.API_BASE_URL}/peleadores/{peleador_id}/icono", files=archivos)
    if resp.status_code == 400:
        raise ImagenInvalidaError(resp.json().get("error", "Imagen inválida"))
    resp.raise_for_status()
    _invalidar_cache_listado()  # que el cambio se vea ya, sin esperar al cache
    return resp.json()


def eliminar_icono(peleador_id):
    requests.delete(f"{Config.API_BASE_URL}/peleadores/{peleador_id}/icono").raise_for_status()


def limpiar_imagenes_rotas():
    resp = requests.post(f"{Config.API_BASE_URL}/peleadores/limpiar-imagenes-rotas")
    resp.raise_for_status()
    _invalidar_cache_listado()  # que el cambio se vea ya, sin esperar al cache
    return resp.json()["limpiadas"]
