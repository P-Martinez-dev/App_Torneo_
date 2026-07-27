class Peleador:
    def __init__(self, id=None, nombre=None):
        self.id = id
        self.nombre = nombre

    def to_dict(self):
        return {"id": self.id, "nombre": self.nombre}

    @staticmethod
    def from_row(row):
        if row is None:
            return None
        return Peleador(id=row["id"], nombre=row["nombre"])