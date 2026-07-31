from flask import request, jsonify


def obtener_json_body():
    """
    request.get_json() puede devolver None si el body vino vacío, con otro
    Content-Type, o es JSON válido pero no un objeto (ej: 'null', '42').
    Esto lo detecta temprano y devuelve un 400 prolijo ya armado, en vez de
    dejar que reviente más abajo con un 500 al hacer .get() sobre None.

    Uso:
        datos, error = obtener_json_body()
        if error:
            return error
        ...datos.get("campo")...
    """
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return None, (jsonify({"error": "El body debe ser un JSON válido (objeto)"}), 400)
    return datos, None
