class AdminUsuario:
    def __init__(self, id=None, usuario=None, password_hash=None, creado_en=None):
        self.id = id
        self.usuario = usuario
        self.password_hash = password_hash
        self.creado_en = creado_en

    def to_dict(self):
        """Nunca incluye password_hash -- ni siquiera hasheada tiene que
        salir de este proceso hacia el frontend."""
        return {
            "id": self.id,
            "usuario": self.usuario,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
        }

    @staticmethod
    def from_row(row):
        if row is None:
            return None
        return AdminUsuario(
            id=row["id"], usuario=row["usuario"], password_hash=row["password_hash"],
            creado_en=row.get("creado_en"),
        )
