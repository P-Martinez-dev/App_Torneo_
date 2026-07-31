class Jugador:
    def __init__(self, id=None, nombre=None, fecha_nacimiento=None,
                 imagen_vertical_path=None, imagen_icono_path=None):
        self.id = id
        self.nombre = nombre
        self.fecha_nacimiento = fecha_nacimiento
        self.imagen_vertical_path = imagen_vertical_path
        self.imagen_icono_path = imagen_icono_path

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "fecha_nacimiento": (
                self.fecha_nacimiento.isoformat() if self.fecha_nacimiento else None
            ),
            "imagen_vertical": self.imagen_vertical_path,
            "imagen_icono": self.imagen_icono_path,
        }

    @staticmethod
    def from_row(row):
        if row is None:
            return None
        return Jugador(
            id=row["id"],
            nombre=row["nombre"],
            fecha_nacimiento=row["fecha_nacimiento"],
            imagen_vertical_path=row.get("imagen_vertical_path"),
            imagen_icono_path=row.get("imagen_icono_path"),
        )
