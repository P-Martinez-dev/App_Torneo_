from services.api_client import session as requests
from config import Config


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
    resp = requests.get(f"{Config.API_BASE_URL}/torneos/nombre-club")
    resp.raise_for_status()
    return resp.json()["nombre_club"]


def actualizar_nombre_club(nombre):
    resp = requests.put(f"{Config.API_BASE_URL}/torneos/nombre-club", json={"nombre": nombre})
    resp.raise_for_status()


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
        if form.get("grupos_tipo") == "manual":
            grupos_dict = {}
            for jid in payload["jugadores_ids"]:
                num_grupo = _a_entero(form.get(f"grupo_de_{jid}"))
                if num_grupo:
                    grupos_dict.setdefault(num_grupo, []).append(jid)
            if grupos_dict:
                payload["grupos_manual"] = [grupos_dict[k] for k in sorted(grupos_dict)]
    elif modo == "cinco_vidas":
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
