from datetime import date
from repositories import torneo_repository
from services import partido_service


class DatosTorneoInvalidosError(Exception):
    pass


def crear_torneo(nombre: str, modo: str, fecha: date, jugadores_ids: list[int],
                  cupos_eliminacion: int | None = None) -> dict:
    if not nombre or not nombre.strip():
        raise DatosTorneoInvalidosError("El nombre del torneo es obligatorio")

    if modo not in ("todos_contra_todos", "grupos_eliminacion", "cinco_vidas"):
        raise DatosTorneoInvalidosError(f"Modo inválido: {modo}")

    if len(jugadores_ids) < 2:
        raise DatosTorneoInvalidosError("Se necesitan al menos 2 jugadores")

    if modo == "grupos_eliminacion":
        if not cantidad_grupos or cantidad_grupos < 2:
            raise DatosTorneoInvalidosError("Se necesita cantidad_grupos válida")
        if cantidad_grupos > len(jugadores_ids):
            raise DatosTorneoInvalidosError("cantidad_grupos no puede superar la cantidad de jugadores")

    torneo_id = torneo_repository.crear(
        nombre.strip(), modo, fecha,
        cupos_eliminacion if modo == "grupos_eliminacion" else None,
    )

    torneo_repository.asignar_jugadores(torneo_id, jugadores_ids)

    partido_service.generar_fixture_inicial(
        torneo_id, modo, jugadores_ids, cupos_eliminacion
    )

    return torneo_repository.obtener_por_id(torneo_id)