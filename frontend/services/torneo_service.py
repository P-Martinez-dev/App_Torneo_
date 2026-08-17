import time

from services.api_client import session as requests
from config import Config

# El nombre del club se muestra en el encabezado de TODAS las páginas, pero
# cambia casi nunca -- sin cachearlo, cada carga de cada pantalla se come un
# viaje entero al backend + una consulta a la base solo para eso. Se guarda
# en memoria por unos segundos y se descarta apenas el admin lo edita, así
# que el cambio se ve igual de inmediato.
_SEGUNDOS_CACHE_NOMBRE = 60
_cache_nombre_club = {"valor": None, "vence_en": 0}


class TorneoInvalidoError(Exception):
    pass


def listar_torneos():
    resp = requests.get(f"{Config.API_BASE_URL}/torneos")
    resp.raise_for_status()
    return resp.json()


def torneo_en_curso():
    """Por la regla de 'un solo torneo activo a la vez', a lo sumo hay uno."""
    return next((t for t in listar_torneos() if t["estado"] == "en_curso"), None)


def eliminar_torneo(torneo_id):
    resp = requests.delete(f"{Config.API_BASE_URL}/torneos/{torneo_id}")
    resp.raise_for_status()


def actualizar_torneo(torneo_id, nombre, fecha, descripcion=None):
    resp = requests.put(
        f"{Config.API_BASE_URL}/torneos/{torneo_id}",
        json={"nombre": nombre, "fecha": fecha, "descripcion": descripcion},
    )
    if resp.status_code == 400:
        raise TorneoInvalidoError(resp.json().get("error", "Datos inválidos"))
    resp.raise_for_status()
    return resp.json()


def obtener_torneo(torneo_id):
    resp = requests.get(f"{Config.API_BASE_URL}/torneos/{torneo_id}")
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def obtener_resumen(torneo_id):
    resp = requests.get(f"{Config.API_BASE_URL}/torneos/{torneo_id}/resumen")
    resp.raise_for_status()
    return resp.json()


def obtener_estadisticas(torneo_id):
    resp = requests.get(f"{Config.API_BASE_URL}/torneos/{torneo_id}/estadisticas")
    resp.raise_for_status()
    return resp.json()


def obtener_config_general():
    resp = requests.get(f"{Config.API_BASE_URL}/torneos/config-general")
    resp.raise_for_status()
    datos = resp.json()
    # Esta respuesta YA trae el nombre del club, así que se aprovecha para
    # llenar el cache -- en las pantallas que llaman acá, el encabezado no
    # necesita pedirlo por separado.
    if datos.get("nombre_club"):
        _cache_nombre_club["valor"] = datos["nombre_club"]
        _cache_nombre_club["vence_en"] = time.time() + _SEGUNDOS_CACHE_NOMBRE
    return datos


def obtener_estadisticas_generales():
    resp = requests.get(f"{Config.API_BASE_URL}/torneos/estadisticas-generales")
    resp.raise_for_status()
    return resp.json()


def obtener_navegacion(torneo_id):
    resp = requests.get(f"{Config.API_BASE_URL}/torneos/{torneo_id}/navegacion")
    resp.raise_for_status()
    return resp.json()


def actualizar_proximo_torneo(fecha):
    resp = requests.put(f"{Config.API_BASE_URL}/torneos/proximo-torneo", json={"fecha": fecha})
    resp.raise_for_status()


def actualizar_descripcion_inicio(descripcion):
    resp = requests.put(f"{Config.API_BASE_URL}/torneos/descripcion-inicio", json={"descripcion": descripcion})
    resp.raise_for_status()


def actualizar_descripcion_tablas(descripcion):
    resp = requests.put(f"{Config.API_BASE_URL}/torneos/descripcion-tablas", json={"descripcion": descripcion})
    resp.raise_for_status()


def obtener_nombre_club():
    if _cache_nombre_club["valor"] is not None and time.time() < _cache_nombre_club["vence_en"]:
        return _cache_nombre_club["valor"]

    resp = requests.get(f"{Config.API_BASE_URL}/torneos/nombre-club")
    resp.raise_for_status()
    nombre = resp.json()["nombre_club"]
    _cache_nombre_club["valor"] = nombre
    _cache_nombre_club["vence_en"] = time.time() + _SEGUNDOS_CACHE_NOMBRE
    return nombre


def _invalidar_cache_nombre_club():
    _cache_nombre_club["valor"] = None
    _cache_nombre_club["vence_en"] = 0


def actualizar_nombre_club(nombre):
    resp = requests.put(f"{Config.API_BASE_URL}/torneos/nombre-club", json={"nombre": nombre})
    resp.raise_for_status()
    _invalidar_cache_nombre_club()  # que el cambio se vea ya, sin esperar a que venza el cache


def actualizar_tile(nombre_tile, visible):
    resp = requests.put(f"{Config.API_BASE_URL}/torneos/tiles/{nombre_tile}", json={"visible": visible})
    resp.raise_for_status()


def exportar_imagen(torneo_id):
    resp = requests.get(f"{Config.API_BASE_URL}/torneos/{torneo_id}/exportar-imagen")
    resp.raise_for_status()
    return resp.content


def exportar_imagen_tabla_general(excluidos_ids=None):
    params = [("excluir", i) for i in (excluidos_ids or [])]
    resp = requests.get(f"{Config.API_BASE_URL}/torneos/tabla-general/exportar-imagen", params=params)
    resp.raise_for_status()
    return resp.content


def tabla_general(excluidos_ids=None):
    params = [("excluir", i) for i in (excluidos_ids or [])]
    resp = requests.get(f"{Config.API_BASE_URL}/torneos/tabla-general", params=params)
    resp.raise_for_status()
    return resp.json()


def crear_torneo(datos):
    resp = requests.post(f"{Config.API_BASE_URL}/torneos", json=datos)
    if resp.status_code == 201:
        return resp.json()
    if resp.status_code == 400:
        raise TorneoInvalidoError(resp.json().get("error", "Datos inválidos"))
    resp.raise_for_status()


def armar_payload_creacion(form):
    """
    Traduce el form (siempre strings) al JSON que espera el backend,
    incluyendo solo los campos que corresponden según el modo elegido --
    mandar cupos_eliminacion en un todos_contra_todos, por ejemplo, no
    rompe nada del lado del backend (los ignora), pero no tiene sentido
    mandarlo.
    """
    modo = form.get("modo")
    payload = {
        "nombre": (form.get("nombre") or "").strip(),
        "modo": modo,
        "fecha": form.get("fecha"),
        "jugadores_ids": [int(j) for j in form.getlist("jugadores_ids")],
        "descripcion": (form.get("descripcion") or "").strip() or None,
    }

    if modo == "grupos_eliminacion":
        payload["cupos_eliminacion"] = _a_entero(form.get("cupos_eliminacion"))
        payload["cantidad_grupos"] = _a_entero(form.get("cantidad_grupos"))
        payload["formato_grupos"] = form.get("formato_grupos") or "todos_contra_todos"
        # El campo de vidas de los grupos tiene otro name que el del modo
        # suelto (vidas_iniciales_grupos) para que los dos puedan convivir
        # en el mismo formulario sin pisarse.
        if payload["formato_grupos"] == "rey_de_la_cancha":
            payload["vidas_iniciales"] = _a_entero(form.get("vidas_iniciales_grupos"))
        if form.get("grupos_tipo") == "manual":
            grupos_dict = {}
            for jid in payload["jugadores_ids"]:
                num_grupo = _a_entero(form.get(f"grupo_de_{jid}"))
                if num_grupo:
                    grupos_dict.setdefault(num_grupo, []).append(jid)
            if grupos_dict:
                payload["grupos_manual"] = [grupos_dict[k] for k in sorted(grupos_dict)]
    elif modo == "rey_de_la_cancha":
        payload["vidas_iniciales"] = _a_entero(form.get("vidas_iniciales"))
        orden = form.getlist("orden_jugadores_ids")
        if orden:
            payload["orden_jugadores_ids"] = [int(j) for j in orden]

    return payload


def _a_entero(valor):
    if valor is None or valor == "":
        return None
    try:
        return int(valor)
    except ValueError:
        return None


def estado_warmup():
    """Progreso del precalentado del backend. Es una consulta liviana (el
    backend responde de memoria, no toca la base), así que se puede
    llamar seguido sin costo."""
    resp = requests.get(f"{Config.API_BASE_URL}/torneos/warmup/progreso", timeout=5)
    resp.raise_for_status()
    return resp.json()


def obtener_infos():
    resp = requests.get(f"{Config.API_BASE_URL}/torneos/infos")
    resp.raise_for_status()
    return resp.json()


def actualizar_info(cual, texto):
    resp = requests.put(f"{Config.API_BASE_URL}/torneos/infos/{cual}", json={"texto": texto})
    resp.raise_for_status()
