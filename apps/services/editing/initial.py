from apps.services.models import Categoria, Servicio


class CategoryInitial:
    @staticmethod
    def of(category: Categoria) -> dict:
        return {
            "name": category.nombre,
            "description": category.descripcion,
            "status": category.estado == Categoria.EstadoChoices.ACTIVO,
        }


class ServiceInitial:
    @staticmethod
    def minutes(duration) -> int:
        if not duration:
            return 0
        return int(duration.total_seconds() // 60)

    @classmethod
    def of(cls, service: Servicio) -> dict:
        return {
            "category": service.categoria_id,
            "name": service.nombre,
            "description": service.descripcion,
            "price": service.precio,
            "duration": cls.minutes(service.duracion_estimada),
            "status": service.estado == Servicio.EstadoChoices.ACTIVO,
        }
