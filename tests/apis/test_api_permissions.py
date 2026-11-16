from django.test import SimpleTestCase
from django.urls import URLPattern, URLResolver

from apis.common.views import ApiView
from apis.v1 import urls as v1_urls
from apps.profiles.permisos import PARA_TODO_EL_EQUIPO, SOLO_ADMINISTRACION


def patterns_of(patterns):
    for pattern in patterns:
        if isinstance(pattern, URLResolver):
            yield from patterns_of(pattern.url_patterns)
        elif isinstance(pattern, URLPattern):
            yield pattern


class ApiPermissionTests(SimpleTestCase):
    def test_every_api_route_is_in_a_permission_list(self):
        for pattern in patterns_of(v1_urls.urlpatterns):
            with self.subTest(route=str(pattern.pattern)):
                self.assertTrue(pattern.name, "route without name")
                self.assertIn(pattern.name, SOLO_ADMINISTRACION | PARA_TODO_EL_EQUIPO, "route without permission")

    def test_every_api_route_goes_through_the_guard_chain(self):
        for pattern in patterns_of(v1_urls.urlpatterns):
            with self.subTest(route=pattern.name):
                self.assertTrue(issubclass(getattr(pattern.callback, "view_class", object), ApiView))
