import threading
import time
import traceback

# Cuánto vive un resultado cacheado si NADIE cambia nada. La invalidación
# real ocurre apenas hay cualquier escritura (ver el gancho en app.py).
_SEGUNDOS_DE_VIDA = 120

# Pausa entre perfil y perfil al calentarlos en segundo plano, para no
# competir con los pedidos de quien está usando la app en ese momento.
_PAUSA_ENTRE_PERFILES = 0.4

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
    """Se llama después de CUALQUIER escritura exitosa.

    Además de vaciar el cache, relanza el calentado de perfiles en segundo
    plano: si no, después de cargar un resultado (justo cuando todos van a
    entrar a mirar cómo quedaron las cosas) los perfiles volverían a estar
    fríos y cada uno tardaría de nuevo."""
    with _lock:
        _guardado.clear()
    if _app_para_recalentar["app"] is not None:
        threading.Thread(target=_recalentar_todo, daemon=True).start()


_app_para_recalentar = {"app": None}


def _recalentar_todo():
    """Rehace el cache después de una escritura: primero lo que se ve al
    entrar, después los perfiles."""
    app = _app_para_recalentar["app"]
    if app is None:
        return
    # Todo adentro del try, imports incluidos -- ver el comentario largo
    # en _run(): un import que falle acá afuera mata el hilo en silencio.
    try:
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
        with app.app_context():
            for _nombre, clave in _PASOS:
                obtener(clave, funciones[clave])
            _calentar_perfiles_en_segundo_plano()
    except Exception:
        traceback.print_exc()


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
    _app_para_recalentar["app"] = app
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
        # TODO adentro del try, imports incluidos: si algo falla acá afuera
        # (por ejemplo un import circular), el hilo muere en silencio y el
        # estado queda congelado en "Conectando..." para siempre -- y como
        # la pantalla de carga espera a "completado", todos se quedan
        # trabados en 0% sin ningún mensaje ni error visible.
        try:
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
            with app.app_context():
                for nombre, clave in _PASOS:
                    with _lock:
                        _estado_warmup["paso_actual"] = nombre
                    print(f">>> WARMUP: empezando '{nombre}'", flush=True)
                    obtener(clave, funciones[clave])
                    print(f">>> WARMUP: terminó '{nombre}'", flush=True)
                    with _lock:
                        _estado_warmup["pasos_hechos"] += 1
                with _lock:
                    _estado_warmup["paso_actual"] = "Listo"
                    _estado_warmup["completado"] = True

                # A partir de acá la app YA es usable (la pantalla de carga
                # desaparece con "completado"). Lo que sigue son los perfiles
                # individuales, que se van calentando de a uno en segundo
                # plano: si entrás a uno ya calentado, es instantáneo; si no,
                # se calcula al momento como siempre. Nadie espera por esto.
                _calentar_perfiles_en_segundo_plano()
        except Exception as e:
            # Si algo falla (base caída al arrancar, por ejemplo), se marca
            # completado igual: es preferible dejar entrar a la app y que
            # muestre el error real, antes que dejar al usuario trabado
            # para siempre en la pantalla de carga.
            traceback.print_exc()  # que el error quede en los logs del servidor
            with _lock:
                _estado_warmup["error"] = str(e)
                _estado_warmup["paso_actual"] = "Listo"
                _estado_warmup["completado"] = True

    threading.Thread(target=_run, daemon=True).start()


# --- Segunda fase: perfiles individuales, sin que nadie espere ---

_estado_perfiles = {"hechos": 0, "totales": 0, "completado": False}


def estado_perfiles():
    with _lock:
        return dict(_estado_perfiles)


def _calentar_perfiles_en_segundo_plano():
    """Calienta el perfil de cada jugador y peleador, de a uno.

    Va con una pausa corta entre cada uno a propósito: la idea es que esto
    NO compita con los pedidos reales de quien está usando la app. Es
    preferible que tarde un rato más en terminar y que la navegación se
    sienta fluida, a calentar rápido pero trabando lo que el usuario está
    mirando ahora.
    """
    try:
        from repositories import jugador_repository, peleador_repository
        from services import estadisticas_service, estadisticas_peleador_service

        jugadores = jugador_repository.obtener_todos()
        peleadores = peleador_repository.obtener_todos()
    except Exception:
        traceback.print_exc()
        return

    with _lock:
        _estado_perfiles.update({
            "hechos": 0,
            "totales": len(jugadores) + len(peleadores),
            "completado": False,
        })

    for j in jugadores:
        try:
            obtener(f"stats-jugador-{j.id}",
                    lambda jid=j.id: estadisticas_service.obtener_estadisticas_jugador(jid))
        except Exception:
            pass  # que falle uno no debe cortar el resto
        with _lock:
            _estado_perfiles["hechos"] += 1
        time.sleep(_PAUSA_ENTRE_PERFILES)

    for p in peleadores:
        try:
            obtener(f"stats-peleador-{p.id}",
                    lambda pid=p.id: estadisticas_peleador_service.obtener_estadisticas_peleador(pid))
        except Exception:
            pass
        with _lock:
            _estado_perfiles["hechos"] += 1
        time.sleep(_PAUSA_ENTRE_PERFILES)

    with _lock:
        _estado_perfiles["completado"] = True