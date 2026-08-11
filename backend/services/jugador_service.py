import os

from mysql.connector import Error
from repositories import jugador_repository
from services import almacenamiento_service


class JugadorNoEncontradoError(Exception):
    pass


class JugadorConHistorialError(Exception):
    """Se lanza al intentar eliminar un jugador que ya participó de partidos/torneos."""
    pass


class ImagenInvalidaError(Exception):
    pass


EXTENSIONES_PERMITIDAS = {"jpg", "jpeg", "png", "webp"}
TAMAÑO_MAXIMO_BYTES = 5 * 1024 * 1024  # 5MB
CARPETA_UPLOADS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads", "jugadores")
CARPETA_STATIC = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")


def limpiar_imagenes_rotas():
    """
    Recorre todos los jugadores y limpia (pone en NULL) las referencias a
    imagen_vertical/imagen_icono que apuntan a un archivo que ya no
    existe en disco -- pasa si en algún momento se reemplazó la carpeta
    static/ entera al actualizar el proyecto, perdiendo los archivos
    subidos pero no las referencias que quedaron en la base. Sin esto,
    el jugador queda mostrando el ícono de imagen rota para siempre.
    Devuelve cuántas referencias se limpiaron.
    """
    jugadores = jugador_repository.obtener_todos()
    limpiadas = 0
    for j in jugadores:
        for campo, path in (
            ("imagen_vertical_path", j.imagen_vertical_path),
            ("imagen_icono_path", j.imagen_icono_path),
        ):
            # Las imágenes de la nube (URL completa) NO se tocan: viven
            # fuera de este disco, así que preguntar si "existen acá" daría
            # que no y las borraría a todas.
            if not path or path.startswith("http"):
                continue
            if not os.path.isfile(os.path.join(CARPETA_STATIC, path)):
                jugador_repository.actualizar_imagen(j.id, campo, None)
                limpiadas += 1
    return limpiadas


def listar_jugadores():
    jugadores = jugador_repository.obtener_todos()
    return [j.to_dict() for j in jugadores]


def obtener_navegacion(jugador_id):
    """IDs del jugador anterior y siguiente, en el mismo orden que se
    listan en el roster (alfabético) -- para las flechas de 'anterior/
    siguiente' del perfil, sin tener que volver al listado y elegir a
    mano."""
    todos = jugador_repository.obtener_todos()
    ids = [j.id for j in todos]
    if jugador_id not in ids:
        return {"anterior_id": None, "siguiente_id": None}
    idx = ids.index(jugador_id)
    return {
        "anterior_id": ids[idx - 1] if idx > 0 else None,
        "siguiente_id": ids[idx + 1] if idx < len(ids) - 1 else None,
    }


def obtener_jugador(jugador_id):
    jugador = jugador_repository.obtener_por_id(jugador_id)
    if jugador is None:
        raise JugadorNoEncontradoError(f"No existe el jugador {jugador_id}")
    return jugador.to_dict()


def crear_jugador(nombre, fecha_nacimiento=None):
    if not nombre or not nombre.strip():
        raise ValueError("El nombre del jugador es obligatorio")
    nuevo_id = jugador_repository.crear(nombre.strip(), fecha_nacimiento)
    return obtener_jugador(nuevo_id)


def actualizar_jugador(jugador_id, nombre, fecha_nacimiento=None):
    if not nombre or not nombre.strip():
        raise ValueError("El nombre del jugador es obligatorio")
    actualizado = jugador_repository.actualizar(jugador_id, nombre.strip(), fecha_nacimiento)
    if not actualizado:
        raise JugadorNoEncontradoError(f"No existe el jugador {jugador_id}")
    return obtener_jugador(jugador_id)


def eliminar_jugador(jugador_id):
    try:
        eliminado = jugador_repository.eliminar(jugador_id)
    except Error as e:
        # error 1451 = "Cannot delete or update a parent row: a foreign key constraint fails"
        if e.errno == 1451:
            raise JugadorConHistorialError(
                "No se puede eliminar un jugador que ya participó en torneos o partidos"
            )
        raise
    if not eliminado:
        raise JugadorNoEncontradoError(f"No existe el jugador {jugador_id}")
    _borrar_archivo_existente(jugador_id, "vertical")
    _borrar_archivo_existente(jugador_id, "icono")


# =========================================================
# Imágenes (vertical grande para el perfil, ícono chico para el grid)
# =========================================================

def subir_imagen_vertical(jugador_id, file_storage):
    return _subir_imagen(jugador_id, file_storage, "vertical", "imagen_vertical_path")


def subir_icono(jugador_id, file_storage):
    return _subir_imagen(jugador_id, file_storage, "icono", "imagen_icono_path")


def eliminar_imagen_vertical(jugador_id):
    return _eliminar_imagen(jugador_id, "vertical", "imagen_vertical_path")


def eliminar_icono(jugador_id):
    return _eliminar_imagen(jugador_id, "icono", "imagen_icono_path")


def _subir_imagen(jugador_id, file_storage, sufijo, campo_db):
    if jugador_repository.obtener_por_id(jugador_id) is None:
        raise JugadorNoEncontradoError(f"No existe el jugador {jugador_id}")

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
        file_storage, f"jugador_{jugador_id}_{sufijo}", "jugadores"
    )
    jugador_repository.actualizar_imagen(jugador_id, campo_db, valor)
    return obtener_jugador(jugador_id)


def _eliminar_imagen(jugador_id, sufijo, campo_db):
    jugador = jugador_repository.obtener_por_id(jugador_id)
    if jugador is None:
        raise JugadorNoEncontradoError(f"No existe el jugador {jugador_id}")
    valor_actual = getattr(jugador, campo_db, None)
    almacenamiento_service.borrar_imagen(
        valor_actual, f"jugador_{jugador_id}_{sufijo}", "jugadores"
    )
    jugador_repository.actualizar_imagen(jugador_id, campo_db, None)
    return obtener_jugador(jugador_id)


def _extension_valida(filename):
    if "." not in filename:
        return None
    ext = filename.rsplit(".", 1)[1].lower()
    return ext if ext in EXTENSIONES_PERMITIDAS else None


def _borrar_archivo_existente(jugador_id, sufijo):
    """Borra cualquier archivo previo jugador_{id}_{sufijo}.* -- puede
    haber cambiado de extensión entre subidas, por eso no alcanza con
    borrar un nombre fijo."""
    if not os.path.isdir(CARPETA_UPLOADS):
        return
    prefijo = f"jugador_{jugador_id}_{sufijo}."
    for nombre in os.listdir(CARPETA_UPLOADS):
        if nombre.startswith(prefijo):
            os.remove(os.path.join(CARPETA_UPLOADS, nombre))