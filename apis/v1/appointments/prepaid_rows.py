from apps.appointments.engine import PrepaidCard

"""========================================================================="""
# region ........ Builders


class PrepaidRows:
    @staticmethod
    def build(rows):
        return [
            {
                "id": row["id"],
                "amount": row["amount"],
                "kind": row["kind"],
                "reservation": row["reservation"],
                "discounts": row["discounts"],
                "method": row["method"],
                "method_label": row["methodLabel"],
                "date": row["date"],
            }
            for row in PrepaidCard(rows).rows_config()
        ]


# endregion
"""========================================================================="""
