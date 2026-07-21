class Jugador:
    def __init__(self, id=None, nombre=None, fecha_nacimiento=None):
        self.id = id
        self.nombre = nombre
        self.fecha_nacimiento = fecha_nacimiento

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "fecha_nacimiento": (
                self.fecha_nacimiento.isoformat() if self.fecha_nacimiento else None
            ),
        }

    @staticmethod
    def from_row(row):
        return Jugador(
            id=row["id"],
            nombre=row["nombre"],
            fecha_nacimiento=row["fecha_nacimiento"],
        )