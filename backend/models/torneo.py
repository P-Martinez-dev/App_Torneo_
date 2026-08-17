class Torneo:
    def __init__(self, id=None, nombre=None, modo=None, fecha=None,
                 estado="planificado", cupos_eliminacion=None, vidas_iniciales=None,
                 formato_grupos=None,
                 descripcion=None):
        self.id = id
        self.nombre = nombre
        self.modo = modo
        self.fecha = fecha
        self.estado = estado
        self.cupos_eliminacion = cupos_eliminacion
        self.vidas_iniciales = vidas_iniciales
        # Solo aplica a grupos_eliminacion. None = 'todos_contra_todos', que
        # era el único formato antes de que se pudiera elegir.
        self.formato_grupos = formato_grupos or "todos_contra_todos"
        self.descripcion = descripcion

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "modo": self.modo,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "estado": self.estado,
            "cupos_eliminacion": self.cupos_eliminacion,
            "vidas_iniciales": self.vidas_iniciales,
            "formato_grupos": self.formato_grupos,
            "descripcion": self.descripcion,
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
            vidas_iniciales=row.get("vidas_iniciales"),
            formato_grupos=row.get("formato_grupos"),
            descripcion=row.get("descripcion"),
        )
