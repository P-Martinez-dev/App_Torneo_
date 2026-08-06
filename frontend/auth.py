from functools import wraps
from flask import session, redirect, url_for, request, flash


def es_admin():
    return session.get("admin_usuario") is not None


def requiere_admin(vista):
    """Decorador para cualquier ruta que cree/edite/borre/suba algo.
    Si no hay sesión de admin, redirige al login en vez de ejecutar la
    vista -- esto es lo que oculta los botones de editar Y lo que
    bloquea el acceso directo por URL si alguien la escribe a mano."""
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if not es_admin():
            flash("Tenés que iniciar sesión como admin para hacer eso.")
            return redirect(url_for("admin.login", siguiente=request.path))
        return vista(*args, **kwargs)
    return envoltura
