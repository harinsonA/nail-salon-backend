class PrepaidSnapshot:
    @staticmethod
    def of(rows):
        return sorted((row.pk, int(row.monto_pago)) for row in rows)

    @classmethod
    def changed(cls, rows, seen):
        return cls.of(rows) != sorted((int(item["id"]), int(item["amount"])) for item in seen)
