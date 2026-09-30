"""
Sesión de requests compartida por todos los services del frontend.

En vez de tocar cada llamada de cada archivo de service (son ~15,
con decenas de requests.get/post/put/delete repartidos), cada service
importa el `session` de acá en vez de importar el módulo `requests`
directo -- como requests.Session tiene los mismos métodos (.get, .post,
etc.) con la misma firma, no hace falta cambiar ninguna otra línea: la
clave interna se manda sola en cada pedido.
"""
import sys
import time

import requests
from config import Config

# (conectar, leer) en segundos. Sin timeout, un backend que no contesta deja
# el pedido colgado indefinidamente; gunicorn mata al worker a los 30 s y
# lo que se ve es un error sin explicación. La lectura corta a los 25 s,
# ANTES que gunicorn, para que el manejador de app.py alcance a mostrar la
# pantalla de carga. Una llamada que necesite otro valor lo pasa explícito
# (ej: estado_warmup usa timeout=5) y ese pisa a este.
TIMEOUT_POR_DEFECTO = (5, 25)

# Pausa ante un 429 ("Too Many Requests"). En Render ese 429 lo contesta la
# plataforma, no el backend (por eso el backend no tiene ningún log): los
# pedidos de este servidor se rechazan antes de llegar. Seguir insistiendo
# solo mantiene el límite activo, así que durante la pausa NO se sale a la
# red: se falla al instante. Si Render manda Retry-After se respeta, dentro
# de estos márgenes (uno absurdo no puede dejar la app parada media hora).
_SEGUNDOS_PAUSA_POR_DEFECTO = 30
_SEGUNDOS_PAUSA_MAXIMA = 120
_pausa = {"hasta": 0.0}


class BackendEnPausaError(requests.exceptions.ConnectionError):
    """Pedido que ni siquiera se hizo porque se está respetando la pausa de
    un 429. Hereda de ConnectionError a propósito: para el resto de la app
    es lo mismo que un backend que no contesta, y el manejador que ya existe
    para eso en app.py (pantalla de carga) lo toma sin cambios."""


def segundos_de_pausa_restantes():
    return max(0.0, _pausa["hasta"] - time.time())


def _pausar_por_429(resp):
    try:
        segundos = int(resp.headers.get("Retry-After", ""))
    except ValueError:
        # Falta, o viene como fecha en vez de segundos: se usa el valor fijo.
        segundos = _SEGUNDOS_PAUSA_POR_DEFECTO
    segundos = min(max(segundos, _SEGUNDOS_PAUSA_POR_DEFECTO), _SEGUNDOS_PAUSA_MAXIMA)
    _pausa["hasta"] = time.time() + segundos
    # A la salida de error, que es lo que Render muestra en los logs del
    # servicio. Sale una vez por pausa (no una por pedido), así el log se
    # puede leer.
    print(
        f"[api-client] 429 de {resp.url} (Retry-After={resp.headers.get('Retry-After')!r}): "
        f"sin pedidos al backend por {segundos}s",
        file=sys.stderr, flush=True,
    )


class _SesionConTimeout(requests.Session):
    """requests.Session no tiene un timeout por defecto configurable: se
    agrega acá, en el único lugar por donde pasan todos los pedidos. Por la
    misma razón, acá vive también la pausa ante un 429: ningún service
    tiene que acordarse de respetarla."""

    def request(self, method, url, **kwargs):
        restante = segundos_de_pausa_restantes()
        if restante > 0:
            raise BackendEnPausaError(f"Backend en pausa por 429, faltan {restante:.0f}s")
        kwargs.setdefault("timeout", TIMEOUT_POR_DEFECTO)
        resp = super().request(method, url, **kwargs)
        if resp.status_code == 429:
            _pausar_por_429(resp)
        return resp


session = _SesionConTimeout()
session.headers.update({"X-Internal-Key": Config.INTERNAL_API_KEY})
