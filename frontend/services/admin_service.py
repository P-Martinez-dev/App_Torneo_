from services.api_client import session as requests
from config import Config


class CredencialesInvalidasError(Exception):
    pass


class AdminInvalidoError(Exception):
    pass


def verificar_credenciales(usuario, password):
    resp = requests.post(
        f"{Config.API_BASE_URL}/admin/login", json={"usuario": usuario, "password": password}
    )
    if resp.status_code == 401:
        raise CredencialesInvalidasError(resp.json().get("error", "Usuario o contraseña incorrectos"))
    resp.raise_for_status()
    return resp.json()


def listar_admins():
    resp = requests.get(f"{Config.API_BASE_URL}/admin")
    resp.raise_for_status()
    return resp.json()


def crear_admin(usuario, password):
    resp = requests.post(f"{Config.API_BASE_URL}/admin", json={"usuario": usuario, "password": password})
    if resp.status_code in (400, 409):
        raise AdminInvalidoError(resp.json().get("error", "No se pudo crear el admin"))
    resp.raise_for_status()
    return resp.json()


def eliminar_admin(admin_id):
    resp = requests.delete(f"{Config.API_BASE_URL}/admin/{admin_id}")
    if resp.status_code == 400:
        raise AdminInvalidoError(resp.json().get("error", "No se pudo eliminar el admin"))
    resp.raise_for_status()


def obtener_estadisticas_config():
    resp = requests.get(f"{Config.API_BASE_URL}/admin/estadisticas-config")
    resp.raise_for_status()
    return resp.json()


def actualizar_estadistica_visible(clave, visible):
    resp = requests.put(f"{Config.API_BASE_URL}/admin/estadisticas-config", json={"clave": clave, "visible": visible})
    resp.raise_for_status()


def descargar_backup():
    resp = requests.get(f"{Config.API_BASE_URL}/admin/backup")
    resp.raise_for_status()
    return resp.content
