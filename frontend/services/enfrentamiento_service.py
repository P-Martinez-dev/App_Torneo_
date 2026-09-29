from services.api_client import session as requests
from config import Config


class EnfrentamientoInvalidoError(Exception):
    pass


def obtener_enfrentamiento(jugador_a_id, jugador_b_id):
    """Devuelve None si alguno de los dos jugadores no existe (404), para
    que la ruta decida qué mostrar -- mismo criterio que obtener_torneo."""
    resp = requests.get(f"{Config.API_BASE_URL}/enfrentamientos/{jugador_a_id}/{jugador_b_id}")
    if resp.status_code == 404:
        return None
    if resp.status_code == 400:
        raise EnfrentamientoInvalidoError(resp.json().get("error", "Enfrentamiento inválido"))
    resp.raise_for_status()
    return resp.json()
