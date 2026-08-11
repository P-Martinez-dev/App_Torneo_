import os

from mysql.connector import Error
from repositories import peleador_repository
from services import almacenamiento_service


class PeleadorNoEncontradoError(Exception):
    pass


class PeleadorConHistorialError(Exception):
    """Se lanza al intentar eliminar un peleador que ya fue usado en algún partido."""
    pass


class ImagenInvalidaError(Exception):
    pass


EXTENSIONES_PERMITIDAS = {"jpg", "jpeg", "png", "webp"}
TAMAÑO_MAXIMO_BYTES = 5 * 1024 * 1024  # 5MB
CARPETA_UPLOADS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads", "peleadores")
CARPETA_STATIC = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")


def limpiar_imagenes_rotas():
    """Mismo criterio que jugador_service.limpiar_imagenes_rotas, para
    los íconos de peleador."""
    peleadores = peleador_repository.obtener_todos()
    limpiadas = 0
    for p in peleadores:
        # Las imágenes de la nube (URL completa) NO se tocan: viven fuera
        # de este disco, así que preguntar si "existen acá" daría que no y
        # las borraría a todas.
        if not p.imagen_icono_path or p.imagen_icono_path.startswith("http"):
            continue
        if not os.path.isfile(os.path.join(CARPETA_STATIC, p.imagen_icono_path)):
            peleador_repository.actualizar_imagen(p.id, None)
            limpiadas += 1
    return limpiadas


def obtener_navegacion(peleador_id):
    """Mismo criterio que jugador_service.obtener_navegacion, en el
    mismo orden en que se listan (alfabético)."""
    todos = peleador_repository.obtener_todos()
    ids = [p.id for p in todos]
    if peleador_id not in ids:
        return {"anterior_id": None, "siguiente_id": None}
    idx = ids.index(peleador_id)
    return {
        "anterior_id": ids[idx - 1] if idx > 0 else None,
        "siguiente_id": ids[idx + 1] if idx < len(ids) - 1 else None,
    }


def listar_peleadores():
    peleadores = peleador_repository.obtener_todos()
    return [p.to_dict() for p in peleadores]


def obtener_peleador(peleador_id):
    peleador = peleador_repository.obtener_por_id(peleador_id)
    if peleador is None:
        raise PeleadorNoEncontradoError(f"No existe el peleador {peleador_id}")
    return peleador.to_dict()


def crear_peleador(nombre):
    if not nombre or not nombre.strip():
        raise ValueError("El nombre del peleador es obligatorio")
    nuevo_id = peleador_repository.crear(nombre.strip())
    return obtener_peleador(nuevo_id)


def actualizar_peleador(peleador_id, nombre):
    if not nombre or not nombre.strip():
        raise ValueError("El nombre del peleador es obligatorio")
    actualizado = peleador_repository.actualizar(peleador_id, nombre.strip())
    if not actualizado:
        raise PeleadorNoEncontradoError(f"No existe el peleador {peleador_id}")
    return obtener_peleador(peleador_id)


def eliminar_peleador(peleador_id):
    try:
        eliminado = peleador_repository.eliminar(peleador_id)
    except Error as e:
        if e.errno == 1451:
            raise PeleadorConHistorialError(
                "No se puede eliminar un peleador que ya fue usado en algún partido"
            )
        raise
    if not eliminado:
        raise PeleadorNoEncontradoError(f"No existe el peleador {peleador_id}")


def subir_icono(peleador_id, file_storage):
    if peleador_repository.obtener_por_id(peleador_id) is None:
        raise PeleadorNoEncontradoError(f"No existe el peleador {peleador_id}")

    if file_storage is None or file_storage.filename == "":
        raise ImagenInvalidaError("No se envió ningún archivo")

    ext = _extension_valida(file_storage.filename)
    if ext is None:
        raise ImagenInvalidaError(
            f"Formato no permitido. Usá: {', '.join(sorted(EXTENSIONES_PERMITIDAS))}"
        )

    file_storage.seek(0, os.SEEK_END)
    tamaño = file_storage.tell()
    file_storage.seek(0)
    if tamaño > TAMAÑO_MAXIMO_BYTES:
        raise ImagenInvalidaError("La imagen no puede superar los 5MB")

    # Dónde termina guardada (nube o disco local) lo decide
    # almacenamiento_service según haya credenciales configuradas.
    valor = almacenamiento_service.guardar_imagen(
        file_storage, f"peleador_{peleador_id}_icono", "peleadores"
    )
    peleador_repository.actualizar_imagen(peleador_id, valor)
    return obtener_peleador(peleador_id)


def eliminar_icono(peleador_id):
    peleador = peleador_repository.obtener_por_id(peleador_id)
    if peleador is None:
        raise PeleadorNoEncontradoError(f"No existe el peleador {peleador_id}")
    almacenamiento_service.borrar_imagen(
        peleador.imagen_icono_path, f"peleador_{peleador_id}_icono", "peleadores"
    )
    peleador_repository.actualizar_imagen(peleador_id, None)
    return obtener_peleador(peleador_id)


def _extension_valida(filename):
    if "." not in filename:
        return None
    ext = filename.rsplit(".", 1)[1].lower()
    return ext if ext in EXTENSIONES_PERMITIDAS else None


def _borrar_archivo_existente(peleador_id):
    """Borra cualquier ícono previo peleador_{id}_icono.* -- puede haber
    cambiado de extensión entre subidas, por eso no alcanza con borrar
    un nombre fijo."""
    if not os.path.isdir(CARPETA_UPLOADS):
        return
    prefijo = f"peleador_{peleador_id}_icono."
    for nombre in os.listdir(CARPETA_UPLOADS):
        if nombre.startswith(prefijo):
            os.remove(os.path.join(CARPETA_UPLOADS, nombre))