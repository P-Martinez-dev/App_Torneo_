import time

from services.api_client import session as requests
from config import Config


class JugadorInvalidoError(Exception):
    pass


class JugadorConHistorialError(Exception):
    pass


class ImagenInvalidaError(Exception):
    pass


# El listado se usa varias veces DENTRO de un mismo pedido (para sacar la
# entidad puntual y para las flechas de navegación). Se guarda unos segundos
# para no repetir el viaje al backend en ese lapso -- el backend igual lo
# tiene cacheado, pero el viaje en sí también cuesta.
_SEGUNDOS_CACHE_LISTADO = 5
_cache_listado = {"valor": None, "vence_en": 0}


def listar_jugadores():
    if _cache_listado["valor"] is not None and time.time() < _cache_listado["vence_en"]:
        return _cache_listado["valor"]
    resp = requests.get(f"{Config.API_BASE_URL}/jugadores")
    resp.raise_for_status()
    datos = resp.json()
    _cache_listado["valor"] = datos
    _cache_listado["vence_en"] = time.time() + _SEGUNDOS_CACHE_LISTADO
    return datos


def _invalidar_cache_listado():
    _cache_listado["valor"] = None
    _cache_listado["vence_en"] = 0


def obtener_rating():
    resp = requests.get(f"{Config.API_BASE_URL}/jugadores/rating")
    resp.raise_for_status()
    return resp.json()


def limpiar_imagenes_rotas():
    resp = requests.post(f"{Config.API_BASE_URL}/jugadores/limpiar-imagenes-rotas")
    resp.raise_for_status()
    _invalidar_cache_listado()  # que el cambio se vea ya, sin esperar al cache
    return resp.json()["limpiadas"]


def obtener_navegacion(jugador_id):
    """Las flechas de anterior/siguiente salen del listado que ya se pide
    igual (y que el backend tiene cacheado), en vez de un pedido aparte:
    es la misma info, y cada viaje al backend cuesta caro contra una base
    remota."""
    todos = listar_jugadores()
    ids = [x["id"] for x in todos]
    if jugador_id not in ids:
        return {"anterior_id": None, "siguiente_id": None}
    idx = ids.index(jugador_id)
    return {
        # Navegación CÍCLICA: desde el primero, "anterior" lleva al último,
        # y desde el último "siguiente" vuelve al primero. Así nunca falta
        # una flecha y se puede recorrer todo dando la vuelta, sin tener
        # que volver al listado al llegar a una punta.
        # (ids[-1] ya es el último por cómo indexa Python, y el módulo se
        # encarga de volver al principio.)
        "anterior_id": ids[idx - 1],
        "siguiente_id": ids[(idx + 1) % len(ids)],
    }


def obtener_jugador(jugador_id):
    """Sale del listado que el backend ya tiene cacheado, en vez de un
    pedido puntual: es exactamente la misma información y ahorra un viaje
    entero, que contra una base remota es lo que más se nota."""
    for x in listar_jugadores():
        if x["id"] == jugador_id:
            return x
    return None


def crear_jugador(nombre, fecha_nacimiento=None):
    resp = requests.post(
        f"{Config.API_BASE_URL}/jugadores",
        json={"nombre": nombre, "fecha_nacimiento": fecha_nacimiento or None},
    )
    if resp.status_code == 400:
        raise JugadorInvalidoError(resp.json().get("error", "Datos inválidos"))
    resp.raise_for_status()
    _invalidar_cache_listado()  # que el cambio se vea ya, sin esperar al cache
    return resp.json()


def actualizar_jugador(jugador_id, nombre, fecha_nacimiento=None):
    resp = requests.put(
        f"{Config.API_BASE_URL}/jugadores/{jugador_id}",
        json={"nombre": nombre, "fecha_nacimiento": fecha_nacimiento or None},
    )
    if resp.status_code == 400:
        raise JugadorInvalidoError(resp.json().get("error", "Datos inválidos"))
    resp.raise_for_status()
    _invalidar_cache_listado()  # que el cambio se vea ya, sin esperar al cache
    return resp.json()


def eliminar_jugador(jugador_id):
    resp = requests.delete(f"{Config.API_BASE_URL}/jugadores/{jugador_id}")
    if resp.status_code == 409:
        raise JugadorConHistorialError(resp.json().get("error", "No se puede eliminar"))
    resp.raise_for_status()
    _invalidar_cache_listado()  # que el cambio se vea ya, sin esperar al cache


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
    _invalidar_cache_listado()  # que el cambio se vea ya, sin esperar al cache
    return resp.json()
