from apps.clients.models import Cliente
from apps.services.models import Categoria, Servicio
from apps.sync.feeds.base import ModelFeed


class ClientFeed(ModelFeed):
    model = Cliente


class CategoryFeed(ModelFeed):
    model = Categoria


class ServiceFeed(ModelFeed):
    model = Servicio
