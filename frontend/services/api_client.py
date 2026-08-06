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

session = requests.Session()
session.headers.update({"X-Internal-Key": Config.INTERNAL_API_KEY})
