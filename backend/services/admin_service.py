from werkzeug.security import generate_password_hash, check_password_hash
from repositories import admin_repository


class CredencialesInvalidasError(Exception):
    pass


class UsuarioYaExisteError(Exception):
    pass


def verificar_credenciales(usuario, password):
    """Devuelve el admin (sin el hash) si las credenciales son correctas,
    o lanza CredencialesInvalidasError si no. El mensaje de error es
    siempre el mismo genérico (no distingue 'usuario no existe' de
    'contraseña incorrecta') para no filtrar qué usuarios existen."""
    admin = admin_repository.obtener_por_usuario((usuario or "").strip())
    if admin is None or not check_password_hash(admin.password_hash, password or ""):
        raise CredencialesInvalidasError("Usuario o contraseña incorrectos")
    return admin.to_dict()


def crear_admin(usuario, password):
    usuario = (usuario or "").strip()
    if not usuario:
        raise ValueError("El usuario es obligatorio")
    if not password or len(password) < 8:
        raise ValueError("La contraseña tiene que tener al menos 8 caracteres")
    if admin_repository.obtener_por_usuario(usuario) is not None:
        raise UsuarioYaExisteError(f"Ya existe un admin con el usuario '{usuario}'")

    password_hash = generate_password_hash(password)
    nuevo_id = admin_repository.crear(usuario, password_hash)
    return admin_repository.obtener_por_usuario(usuario).to_dict()


def listar_admins():
    return [a.to_dict() for a in admin_repository.obtener_todos()]


def hay_algun_admin():
    return admin_repository.contar() > 0


def eliminar_admin(admin_id):
    if admin_repository.contar() <= 1:
        raise ValueError("No se puede eliminar el último admin -- te quedarías sin forma de entrar")
    return admin_repository.eliminar(admin_id)
