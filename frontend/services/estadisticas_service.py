from services.api_client import session as requests
from config import Config


def obtener_estadisticas(jugador_id):
    resp = requests.get(f"{Config.API_BASE_URL}/jugadores/{jugador_id}/estadisticas")
    resp.raise_for_status()
    return resp.json()
