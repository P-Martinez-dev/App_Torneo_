class Torneo:
    def __init__(self, id=None, nombre=None, modo=None, fecha=None,
                 estado="planificado", cupos_eliminacion=None):
        self.id = id
        self.nombre = nombre
        self.modo = modo
        self.fecha = fecha
        self.estado = estado
        self.cupos_eliminacion = cupos_eliminacion

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "modo": self.modo,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "estado": self.estado,
            "cupos_eliminacion": self.cupos_eliminacion,
        }

    @staticmethod
    def from_row(row):
        if row is None:
            return None
        return Torneo(
            id=row["id"],
            nombre=row["nombre"],
            modo=row["modo"],
            fecha=row["fecha"],
            estado=row["estado"],
            cupos_eliminacion=row["cupos_eliminacion"],
        )