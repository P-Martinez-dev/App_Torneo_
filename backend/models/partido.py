class Partido:
    def __init__(self, id=None, torneo_id=None, jugador1_id=None, jugador2_id=None,
                 ganador_id=None, fase=None, ronda=None, jornada=None, orden=None,
                 grupo_id=None, estado="pendiente", fecha_jugado=None):
        self.id = id
        self.torneo_id = torneo_id
        self.jugador1_id = jugador1_id
        self.jugador2_id = jugador2_id
        self.ganador_id = ganador_id
        self.fase = fase
        self.ronda = ronda
        self.jornada = jornada
        self.orden = orden
        self.grupo_id = grupo_id
        self.estado = estado
        self.fecha_jugado = fecha_jugado

    def to_dict(self):
        return {
            "id": self.id,
            "torneo_id": self.torneo_id,
            "jugador1_id": self.jugador1_id,
            "jugador2_id": self.jugador2_id,
            "ganador_id": self.ganador_id,
            "fase": self.fase,
            "ronda": self.ronda,
            "jornada": self.jornada,
            "orden": self.orden,
            "grupo_id": self.grupo_id,
            "estado": self.estado,
            "fecha_jugado": self.fecha_jugado.isoformat() if self.fecha_jugado else None,
        }

    @staticmethod
    def from_row(row):
        if row is None:
            return None
        return Partido(
            id=row["id"],
            torneo_id=row["torneo_id"],
            jugador1_id=row["jugador1_id"],
            jugador2_id=row["jugador2_id"],
            ganador_id=row["ganador_id"],
            fase=row["fase"],
            ronda=row["ronda"],
            jornada=row["jornada"],
            orden=row["orden"],
            grupo_id=row["grupo_id"],
            estado=row["estado"],
            fecha_jugado=row["fecha_jugado"],
        )