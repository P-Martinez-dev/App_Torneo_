import requests
from config import Config


class PartidoInvalidoError(Exception):
    pass


class ClasificacionInvalidaError(Exception):
    pass


class BracketInvalidoError(Exception):
    pass


def obtener_estado_actual(torneo_id):
    resp = requests.get(f"{Config.API_BASE_URL}/torneos/{torneo_id}/estado-actual")
    resp.raise_for_status()
    return resp.json()


def listar_pendientes(torneo_id):
    resp = requests.get(f"{Config.API_BASE_URL}/torneos/{torneo_id}/partidos-pendientes")
    resp.raise_for_status()
    return resp.json()


def seleccionar_partido(torneo_id, partido_id):
    """Pone otro partido en pantalla; el que estaba antes queda pospuesto."""
    resp = requests.post(
        f"{Config.API_BASE_URL}/torneos/{torneo_id}/partido-actual",
        json={"partido_id": partido_id},
    )
    if resp.status_code == 400:
        raise PartidoInvalidoError(resp.json().get("error", "Partido inválido"))
    resp.raise_for_status()


def cargar_resultado(partido_id, ganador_id, peleador1_id=None, peleador2_id=None, rondas_jugadas=None):
    resp = requests.post(
        f"{Config.API_BASE_URL}/partidos/{partido_id}/resultado",
        json={
            "ganador_id": ganador_id, "peleador1_id": peleador1_id,
            "peleador2_id": peleador2_id, "rondas_jugadas": rondas_jugadas,
        },
    )
    if resp.status_code == 400:
        raise PartidoInvalidoError(resp.json().get("error", "Resultado inválido"))
    resp.raise_for_status()


def obtener_bracket(torneo_id):
    resp = requests.get(f"{Config.API_BASE_URL}/torneos/{torneo_id}/bracket")
    resp.raise_for_status()
    return resp.json()


def resembrar_bracket(torneo_id, emparejamientos):
    resp = requests.put(
        f"{Config.API_BASE_URL}/torneos/{torneo_id}/bracket",
        json={"emparejamientos": emparejamientos},
    )
    if resp.status_code == 400:
        raise BracketInvalidoError(resp.json().get("error", "Bracket inválido"))
    resp.raise_for_status()


def marcar_no_realizado(partido_id):
    resp = requests.post(f"{Config.API_BASE_URL}/partidos/{partido_id}/no-realizado")
    if resp.status_code == 400:
        raise PartidoInvalidoError(resp.json().get("error", "No se pudo descartar el partido"))
    resp.raise_for_status()


def forzar_clasificado(torneo_id, jugador_id, clasificado, observacion=None):
    resp = requests.post(
        f"{Config.API_BASE_URL}/torneos/{torneo_id}/forzar-clasificado",
        json={"jugador_id": jugador_id, "clasificado": clasificado, "observacion": observacion},
    )
    if resp.status_code == 400:
        raise ClasificacionInvalidaError(resp.json().get("error", "Datos inválidos"))
    resp.raise_for_status()


def reintentar_desempate(torneo_id, jugadores_empatados_ids, slots):
    resp = requests.post(
        f"{Config.API_BASE_URL}/torneos/{torneo_id}/reintentar-desempate",
        json={"jugadores_empatados_ids": jugadores_empatados_ids, "slots": slots},
    )
    if resp.status_code == 400:
        raise ClasificacionInvalidaError(resp.json().get("error", "Datos inválidos"))
    resp.raise_for_status()
