"""
Sesión de requests compartida por todos los services del frontend.

En vez de tocar cada llamada de cada archivo de service (son ~15,
con decenas de requests.get/post/put/delete repartidos), cada service
importa el `session` de acá en vez de importar el módulo `requests`
directo -- como requests.Session tiene los mismos métodos (.get, .post,
etc.) con la misma firma, no hace falta cambiar ninguna otra línea: la
clave interna se manda sola en cada pedido.
"""
import requests
from config import Config

# (conectar, leer) en segundos. Sin timeout, un backend que no contesta deja
# el pedido colgado indefinidamente; gunicorn mata al worker a los 30 s y
# lo que se ve es un error sin explicación. La lectura corta a los 25 s,
# ANTES que gunicorn, para que el manejador de app.py alcance a mostrar la
# pantalla de carga. Una llamada que necesite otro valor lo pasa explícito
# (ej: estado_warmup usa timeout=5) y ese pisa a este.
TIMEOUT_POR_DEFECTO = (5, 25)


class _SesionConTimeout(requests.Session):
    """requests.Session no tiene un timeout por defecto configurable: se
    agrega acá, en el único lugar por donde pasan todos los pedidos."""

    def request(self, method, url, **kwargs):
        kwargs.setdefault("timeout", TIMEOUT_POR_DEFECTO)
        return super().request(method, url, **kwargs)


session = _SesionConTimeout()
session.headers.update({"X-Internal-Key": Config.INTERNAL_API_KEY})
