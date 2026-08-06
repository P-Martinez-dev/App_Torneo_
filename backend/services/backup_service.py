import io
import json
import os
import zipfile
from datetime import datetime

from services import torneo_service, tabla_general_service, jugador_service, peleador_service

CARPETA_UPLOADS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads")


def generar_backup_completo():
    """
    Arma un .zip con el JSON de todos los datos + todas las imágenes
    subidas, todo en un solo archivo -- lo mismo que hace
    exportar_backup.py por consola, pero corriendo en el propio proceso
    (no hace falta abrir una terminal para tenerlo).
    """
    datos = _armar_datos()

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("backup_datos.json", json.dumps(datos, ensure_ascii=False, indent=2, default=str))

        if os.path.isdir(CARPETA_UPLOADS):
            for raiz, _dirs, archivos in os.walk(CARPETA_UPLOADS):
                for nombre_archivo in archivos:
                    ruta_completa = os.path.join(raiz, nombre_archivo)
                    ruta_relativa = os.path.join("imagenes", os.path.relpath(ruta_completa, CARPETA_UPLOADS))
                    zf.write(ruta_completa, ruta_relativa)

    buffer.seek(0)
    return buffer


def _armar_datos():
    todos_los_torneos = torneo_service.listar_torneos()

    return {
        "exportado_el": datetime.now().isoformat(),
        "torneos": [torneo_service.obtener_resumen(t["id"]) for t in todos_los_torneos],
        "tabla_general": tabla_general_service.calcular_tabla_general(),
        "jugadores": jugador_service.listar_jugadores(),
        "peleadores": peleador_service.listar_peleadores(),
    }
