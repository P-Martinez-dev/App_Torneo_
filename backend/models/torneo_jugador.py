class TorneoJugador:
    """Fila base: participación de un jugador en un torneo, común a los 3 modos."""

    def __init__(self, id=None, torneo_id=None, jugador_id=None):
        self.id = id
        self.torneo_id = torneo_id
        self.jugador_id = jugador_id

    def to_dict(self):
        return {"id": self.id, "torneo_id": self.torneo_id, "jugador_id": self.jugador_id}

    @staticmethod
    def from_row(row):
        if row is None:
            return None
        return TorneoJugador(id=row["id"], torneo_id=row["torneo_id"], jugador_id=row["jugador_id"])


class TorneoJugadorGrupo:
    """Extensión: solo existe para torneos modo 'grupos_eliminacion'."""

    def __init__(self, torneo_jugador_id=None, grupo_id=None, clasificado=None,
                 clasificacion_forzada=False, observacion_forzado=None):
        self.torneo_jugador_id = torneo_jugador_id
        self.grupo_id = grupo_id
        self.clasificado = clasificado
        self.clasificacion_forzada = clasificacion_forzada
        self.observacion_forzado = observacion_forzado

    def to_dict(self):
        return {
            "torneo_jugador_id": self.torneo_jugador_id,
            "grupo_id": self.grupo_id,
            "clasificado": self.clasificado,
            "clasificacion_forzada": self.clasificacion_forzada,
            "observacion_forzado": self.observacion_forzado,
        }

    @staticmethod
    def from_row(row):
        if row is None:
            return None
        return TorneoJugadorGrupo(
            torneo_jugador_id=row["torneo_jugador_id"],
            grupo_id=row["grupo_id"],
            clasificado=row["clasificado"],
            clasificacion_forzada=row["clasificacion_forzada"],
            observacion_forzado=row["observacion_forzado"],
        )


class TorneoJugadorVidas:
    """Extensión: solo existe para torneos modo 'cinco_vidas'."""

    def __init__(self, torneo_jugador_id=None, vidas=3, eliminado=False,
                 posicion_cola=None, en_cancha=False, orden_eliminacion=None):
        self.torneo_jugador_id = torneo_jugador_id
        self.vidas = vidas
        self.eliminado = eliminado
        self.posicion_cola = posicion_cola
        self.en_cancha = en_cancha
        self.orden_eliminacion = orden_eliminacion

    def to_dict(self):
        return {
            "torneo_jugador_id": self.torneo_jugador_id,
            "vidas": self.vidas,
            "eliminado": self.eliminado,
            "posicion_cola": self.posicion_cola,
            "en_cancha": self.en_cancha,
            "orden_eliminacion": self.orden_eliminacion,
        }

    @staticmethod
    def from_row(row):
        if row is None:
            return None
        return TorneoJugadorVidas(
            torneo_jugador_id=row["torneo_jugador_id"],
            vidas=row["vidas"],
            eliminado=row["eliminado"],
            posicion_cola=row["posicion_cola"],
            en_cancha=row["en_cancha"],
            orden_eliminacion=row["orden_eliminacion"],
        )