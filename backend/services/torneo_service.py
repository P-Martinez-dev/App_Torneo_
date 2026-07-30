from datetime import date

from repositories import torneo_repository, grupo_repository, partido_repository, jugador_repository
from services import partido_service, tabla_service, tabla_general_service


class DatosTorneoInvalidosError(Exception):
    pass


class TorneoNoEncontradoError(Exception):
    pass


def obtener_torneo(torneo_id: int) -> dict:
    torneo = torneo_repository.obtener_por_id(torneo_id)
    if torneo is None:
        raise TorneoNoEncontradoError(f"No existe el torneo {torneo_id}")
    return torneo.to_dict()


def listar_torneos() -> list[dict]:
    return [t.to_dict() for t in torneo_repository.obtener_todos()]


def eliminar_torneo(torneo_id: int) -> None:
    eliminado = torneo_repository.eliminar_completo(torneo_id)
    if not eliminado:
        raise TorneoNoEncontradoError(f"No existe el torneo {torneo_id}")


def _es_potencia_de_dos(n):
    return n > 0 and (n & (n - 1)) == 0


def crear_torneo(nombre: str, modo: str, fecha: date, jugadores_ids: list[int],
                  cupos_eliminacion: int | None = None,
                  cantidad_grupos: int | None = None,
                  vidas_iniciales: int | None = None) -> dict:
    if not nombre or not nombre.strip():
        raise DatosTorneoInvalidosError("El nombre del torneo es obligatorio")

    if not fecha:
        raise DatosTorneoInvalidosError("La fecha del torneo es obligatoria")

    if modo not in ("todos_contra_todos", "grupos_eliminacion", "cinco_vidas"):
        raise DatosTorneoInvalidosError(f"Modo inválido: {modo}")

    if len(jugadores_ids) < 2:
        raise DatosTorneoInvalidosError("Se necesitan al menos 2 jugadores")

    if len(set(jugadores_ids)) != len(jugadores_ids):
        raise DatosTorneoInvalidosError("jugadores_ids no puede tener jugadores repetidos")

    existentes = jugador_repository.obtener_ids_existentes(jugadores_ids)
    inexistentes = [jid for jid in jugadores_ids if jid not in existentes]
    if inexistentes:
        raise DatosTorneoInvalidosError(
            f"No existen jugadores con id: {inexistentes}"
        )

    if modo == "grupos_eliminacion":
        if not cupos_eliminacion or cupos_eliminacion < 2:
            raise DatosTorneoInvalidosError(
                "El modo grupos_eliminacion requiere cupos_eliminacion válido"
            )
        if not _es_potencia_de_dos(cupos_eliminacion):
            raise DatosTorneoInvalidosError(
                "cupos_eliminacion debe ser potencia de 2 (4, 8, 16, 32...)"
            )
        if cupos_eliminacion > len(jugadores_ids):
            raise DatosTorneoInvalidosError(
                "cupos_eliminacion no puede superar la cantidad de jugadores"
            )
        if not cantidad_grupos or cantidad_grupos < 2:
            raise DatosTorneoInvalidosError("Se necesita cantidad_grupos válida")
        if cantidad_grupos > len(jugadores_ids):
            raise DatosTorneoInvalidosError(
                "cantidad_grupos no puede superar la cantidad de jugadores"
            )
        tamaño_grupo_mas_chico = len(jugadores_ids) // cantidad_grupos
        if tamaño_grupo_mas_chico < 3:
            raise DatosTorneoInvalidosError(
                f"Con {len(jugadores_ids)} jugadores y {cantidad_grupos} grupos, "
                f"algún grupo quedaría con menos de 3 jugadores. Reducí cantidad_grupos."
            )

    if modo == "cinco_vidas":
        if not isinstance(vidas_iniciales, int) or isinstance(vidas_iniciales, bool) or vidas_iniciales < 1:
            raise DatosTorneoInvalidosError(
                "El modo cinco_vidas requiere vidas_iniciales (un entero >= 1)"
            )

    torneo_id = torneo_repository.crear(
        nombre.strip(), modo, fecha,
        cupos_eliminacion if modo == "grupos_eliminacion" else None,
        vidas_iniciales if modo == "cinco_vidas" else None,
    )

    torneo_repository.asignar_jugadores(torneo_id, jugadores_ids)

    partido_service.generar_fixture_inicial(
        torneo_id, modo, jugadores_ids, cupos_eliminacion, cantidad_grupos, vidas_iniciales
    )
    torneo_repository.marcar_en_curso(torneo_id)

    return torneo_repository.obtener_por_id(torneo_id).to_dict()


# =========================================================
# Resumen del torneo (pensado para "cómo se desarrolló", sobre todo
# útil una vez finalizado, pero funciona en cualquier estado)
# =========================================================

NOMBRES_RONDA = {1: "Final", 2: "Semifinal", 4: "Cuartos de final", 8: "Octavos de final"}


def obtener_resumen(torneo_id: int) -> dict:
    torneo = torneo_repository.obtener_por_id(torneo_id)
    if torneo is None:
        raise TorneoNoEncontradoError(f"No existe el torneo {torneo_id}")

    nombres = {j.id: j.nombre for j in jugador_repository.obtener_todos()}
    partidos = partido_repository.obtener_por_torneo(torneo_id)  # ya viene ordenado por 'orden'

    def con_nombres(p):
        d = p.to_dict()
        d["jugador1_nombre"] = nombres.get(p.jugador1_id)
        d["jugador2_nombre"] = nombres.get(p.jugador2_id)
        d["ganador_nombre"] = nombres.get(p.ganador_id)
        return d

    resumen = {"torneo": torneo.to_dict()}

    if torneo.modo == "todos_contra_todos":
        resumen["tabla"] = tabla_service.calcular_tabla_todos_contra_todos(torneo_id)
        resumen["partidos"] = [con_nombres(p) for p in partidos]

    elif torneo.modo == "cinco_vidas":
        resumen["partidos"] = [con_nombres(p) for p in partidos]

    elif torneo.modo == "grupos_eliminacion":
        grupos = grupo_repository.obtener_por_torneo(torneo_id)
        resumen["grupos"] = [
            {
                **g.to_dict(),
                "tabla": tabla_service.calcular_tabla_grupo(g.id),
                "partidos": [con_nombres(p) for p in partidos if p.grupo_id == g.id],
            }
            for g in grupos
        ]
        resumen["bracket"] = _armar_bracket(partidos, con_nombres)

    if torneo.estado == "finalizado":
        resumen["podio"] = _resumen_podio(torneo, nombres)

    return resumen


def _armar_bracket(partidos, con_nombres):
    partidos_elim = [p for p in partidos if p.fase == "eliminacion"]
    if not partidos_elim:
        return None

    por_ronda = {}
    for p in partidos_elim:
        por_ronda.setdefault(p.ronda, []).append(p)

    rondas = [
        {
            "ronda": ronda,
            "nombre": NOMBRES_RONDA.get(len(por_ronda[ronda]), f"Ronda de {len(por_ronda[ronda]) * 2}"),
            "partidos": [con_nombres(p) for p in por_ronda[ronda]],
        }
        for ronda in sorted(por_ronda)
    ]

    bracket = {"rondas": rondas}
    partido_tercer = next((p for p in partidos if p.fase == "tercer_puesto"), None)
    if partido_tercer:
        bracket["tercer_puesto"] = con_nombres(partido_tercer)
    return bracket


def _resumen_podio(torneo, nombres):
    puestos = tabla_general_service.calcular_puestos(torneo)
    podio = [
        {"jugador_id": jugador_id, "nombre": nombres.get(jugador_id), "puesto": puesto}
        for jugador_id, puesto in puestos.items()
    ]
    podio.sort(key=lambda f: f["puesto"])
    return podio