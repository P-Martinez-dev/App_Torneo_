import threading
import time

# Cuánto vive un resultado cacheado si NADIE cambia nada. La invalidación
# real ocurre apenas hay cualquier escritura (ver el gancho en app.py).
_SEGUNDOS_DE_VIDA = 120

_lock = threading.Lock()
_guardado = {}

_estado_warmup = {
    "iniciado": False,
    "completado": False,
    "paso_actual": None,
    "pasos_hechos": 0,
    "pasos_totales": 0,
    "error": None,
}


def obtener(clave, calcular):
    """Devuelve el resultado cacheado, o lo calcula y lo guarda."""
    with _lock:
        entrada = _guardado.get(clave)
        if entrada is not None and time.time() < entrada["vence_en"]:
            return entrada["valor"]

    valor = calcular()

    with _lock:
        _guardado[clave] = {"valor": valor, "vence_en": time.time() + _SEGUNDOS_DE_VIDA}
    return valor


def invalidar_todo():
    """Se llama después de CUALQUIER escritura exitosa."""
    with _lock:
        _guardado.clear()


def estado_warmup():
    with _lock:
        return dict(_estado_warmup)


# Lo que se precalcula al arrancar: SOLO lo que se ve en la navegación
# normal. Los perfiles individuales de cada jugador/peleador quedan
# afuera a propósito -- son ~60 cálculos pesados y casi nadie los abre
# todos en una sesión, así que se cachean recién cuando alguien entra a
# uno (paga ~2s esa vez, y queda listo).
_PASOS = [
    ("Configuración",           "config-general"),
    ("Listado de torneos",      "listado-torneos"),
    ("Listado de jugadores",    "listado-jugadores"),
    ("Listado de peleadores",   "listado-peleadores"),
    ("Tabla de posiciones",     "tabla-general:[]"),
    ("Estadísticas generales",  "estadisticas-generales"),
]


def calentar(app):
    """Precalcula lo pesado al arrancar, en un hilo aparte. El progreso
    queda disponible para que el frontend muestre una barra real."""
    with _lock:
        _estado_warmup.update({
            "iniciado": True,
            "completado": False,
            "pasos_hechos": 0,
            "pasos_totales": len(_PASOS),
            "paso_actual": "Conectando...",
            "error": None,
        })

    def _run():
        from services import (
            estadisticas_generales_service, tabla_general_service,
            torneo_service, jugador_service, peleador_service,
        )
        funciones = {
            "config-general":         estadisticas_generales_service.obtener_config_general,
            "listado-torneos":        torneo_service.listar_torneos,
            "listado-jugadores":      jugador_service.listar_jugadores,
            "listado-peleadores":     peleador_service.listar_peleadores,
            "tabla-general:[]":       tabla_general_service.calcular_tabla_general,
            "estadisticas-generales": estadisticas_generales_service.obtener_estadisticas_generales,
        }
        try:
            with app.app_context():
                for nombre, clave in _PASOS:
                    with _lock:
                        _estado_warmup["paso_actual"] = nombre
                    obtener(clave, funciones[clave])
                    with _lock:
                        _estado_warmup["pasos_hechos"] += 1
                with _lock:
                    _estado_warmup["paso_actual"] = "Listo"
                    _estado_warmup["completado"] = True
        except Exception as e:
            # Si algo falla (base caída al arrancar, por ejemplo), se marca
            # completado igual: es preferible dejar entrar a la app y que
            # muestre el error real, antes que dejar al usuario trabado
            # para siempre en la pantalla de carga.
            with _lock:
                _estado_warmup["error"] = str(e)
                _estado_warmup["completado"] = True

    threading.Thread(target=_run, daemon=True).start()
