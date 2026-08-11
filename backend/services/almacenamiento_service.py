"""
Dónde se guardan las imágenes de jugadores y peleadores.

Hay dos modos, y el que se usa depende de si hay credenciales de
Cloudinary configuradas:

  - CON Cloudinary: la imagen se sube a la nube y en la base se guarda
    la URL completa. Es lo que hace falta en producción, porque el disco
    del servidor se borra en cada reinicio y las fotos se perderían.

  - SIN Cloudinary (desarrollo local): se guarda en backend/static/uploads
    como siempre, y en la base queda la ruta relativa. Así se puede
    trabajar en local sin necesitar credenciales de nada.

El resto del código no necesita saber cuál de los dos está activo: llama
a guardar_imagen() y recibe el valor que hay que guardar en la base.
"""
import os

CLOUDINARY_URL = os.getenv("CLOUDINARY_URL", "").strip()
_cloudinary = None


def hay_nube():
    """True si está configurado el almacenamiento en la nube."""
    return bool(CLOUDINARY_URL)


def _sdk():
    """Importa y configura el SDK de Cloudinary la primera vez que hace
    falta -- así el proyecto arranca igual aunque la librería no esté
    instalada, mientras no se use el modo nube."""
    global _cloudinary
    if _cloudinary is None:
        import cloudinary
        import cloudinary.uploader
        # cloudinary lee CLOUDINARY_URL del entorno automáticamente
        cloudinary.config(secure=True)
        _cloudinary = cloudinary
    return _cloudinary


def guardar_imagen(file_storage, identificador, carpeta):
    """
    Guarda la imagen y devuelve lo que hay que persistir en la base:
    una URL completa (modo nube) o una ruta relativa (modo local).

    identificador: nombre único y estable, ej "jugador_12_icono".
    carpeta: "jugadores" o "peleadores".
    """
    if hay_nube():
        resultado = _sdk().uploader.upload(
            file_storage,
            public_id=f"app-torneo/{carpeta}/{identificador}",
            overwrite=True,          # reemplaza la anterior del mismo jugador
            invalidate=True,         # y limpia la copia vieja del CDN
            resource_type="image",
        )
        return resultado["secure_url"]

    # --- modo local ---
    carpeta_destino = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "static", "uploads", carpeta
    )
    os.makedirs(carpeta_destino, exist_ok=True)
    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    nombre_archivo = f"{identificador}.{ext}"
    _borrar_locales_previos(carpeta_destino, identificador)
    file_storage.save(os.path.join(carpeta_destino, nombre_archivo))
    return f"uploads/{carpeta}/{nombre_archivo}"


def borrar_imagen(valor_guardado, identificador, carpeta):
    """Borra la imagen que corresponde a lo que había guardado en la base.
    No falla si el archivo ya no existe -- borrar algo que no está no es
    un error para quien llama."""
    if not valor_guardado:
        return

    if valor_guardado.startswith("http"):
        try:
            _sdk().uploader.destroy(
                f"app-torneo/{carpeta}/{identificador}", invalidate=True
            )
        except Exception:
            pass
        return

    carpeta_destino = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "static", "uploads", carpeta
    )
    _borrar_locales_previos(carpeta_destino, identificador)


def _borrar_locales_previos(carpeta_destino, identificador):
    """Borra cualquier archivo {identificador}.* -- puede haber quedado
    uno con otra extensión de una subida anterior."""
    if not os.path.isdir(carpeta_destino):
        return
    for nombre in os.listdir(carpeta_destino):
        if nombre.rsplit(".", 1)[0] == identificador:
            try:
                os.remove(os.path.join(carpeta_destino, nombre))
            except OSError:
                pass