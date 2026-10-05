from simple_history.models import HistoricalRecords


class HistorialRecords(HistoricalRecords):
    def get_meta_options(self, model):
        opciones = super().get_meta_options(model)
        opciones["db_table"] = f"{model._meta.db_table}_historial"
        return opciones
