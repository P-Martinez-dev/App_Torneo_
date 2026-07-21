class Grupo:
    def __init__(self, id=None, torneo_id=None, nombre=None,
                 tipo="grupo", slots_a_clasificar=None):
        self.id = id
        self.torneo_id = torneo_id
        self.nombre = nombre
        self.tipo = tipo  # 'grupo' | 'repechaje' | 'desempate'
        self.slots_a_clasificar = slots_a_clasificar

    def to_dict(self):
        return {
            "id": self.id,
            "torneo_id": self.torneo_id,
            "nombre": self.nombre,
            "tipo": self.tipo,
            "slots_a_clasificar": self.slots_a_clasificar,
        }

    @staticmethod
    def from_row(row):
        if row is None:
            return None
        return Grupo(
            id=row["id"],
            torneo_id=row["torneo_id"],
            nombre=row["nombre"],
            tipo=row["tipo"],
            slots_a_clasificar=row["slots_a_clasificar"],
        )