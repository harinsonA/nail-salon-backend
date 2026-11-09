from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.db import connection, transaction

from apps.profiles.models import Perfil
from apps.tenancy.models import Negocio
from apps.tenancy.user_limit import UserLimit
from tests.base import NegocioTestCase

User = get_user_model()


class UserLimitTests(NegocioTestCase):
    esquema = "limite"

    def setUp(self):
        super().setUp()
        self.owner = self.member("carla", Perfil.Rol.PROPIETARIO)

    def member(self, name, role=Perfil.Rol.COLABORADOR, active=True):
        user = User.objects.create_user(
            username=name, email=f"{name}@correo.cl", password="x", is_active=active
        )
        Perfil.objects.filter(user=user).update(rol=role)
        return User.objects.select_related("perfil").get(pk=user.pk)

    def with_limit(self, limit):
        Negocio.objects.filter(pk=self.negocio.pk).update(limite_usuarios=limit)
        self.negocio.refresh_from_db()
        return UserLimit(self.negocio)

    def test_null_means_unlimited(self):
        self.member("ana")
        user_limit = self.with_limit(None)
        self.assertEqual(
            (
                user_limit.is_unlimited,
                user_limit.has_free_seat,
                user_limit.is_over_limit,
                user_limit.excess,
                user_limit.can_manage_members,
                user_limit.team_enabled,
                user_limit.usage_label,
            ),
            (True, True, False, 0, True, True, "2 / sin límite"),
        )

    def test_only_active_accounts_count(self):
        self.member("ana")
        self.member("bea", active=False)
        user_limit = self.with_limit(3)
        self.assertEqual(user_limit.active_count, 2)
        self.assertTrue(user_limit.has_free_seat)
        self.assertEqual(user_limit.usage_label, "2 / 3")

    def test_limit_one_with_only_the_owner_has_no_team(self):
        user_limit = self.with_limit(1)
        self.assertEqual(
            (
                user_limit.active_count,
                user_limit.has_free_seat,
                user_limit.is_over_limit,
                user_limit.team_enabled,
            ),
            (1, False, False, False),
        )

    def test_limit_two_has_team_and_a_free_seat(self):
        user_limit = self.with_limit(2)
        self.assertTrue(user_limit.team_enabled)
        self.assertTrue(user_limit.has_free_seat)
        self.member("ana")
        self.assertFalse(self.with_limit(2).has_free_seat)

    def test_over_the_limit_only_the_owner_gets_in(self):
        manager = self.member("ana", Perfil.Rol.ENCARGADO)
        collaborator = self.member("bea")
        user_limit = self.with_limit(1)
        self.assertEqual(
            (
                user_limit.is_over_limit,
                user_limit.excess,
                user_limit.can_manage_members,
                user_limit.team_enabled,
                user_limit.usage_label,
            ),
            (True, 2, False, True, "3 / 1"),
        )
        self.assertTrue(user_limit.lets_in(self.owner))
        self.assertFalse(user_limit.lets_in(manager))
        self.assertFalse(user_limit.lets_in(collaborator))
        self.assertTrue(self.with_limit(3).lets_in(collaborator))

    def test_for_request_reads_the_tenant(self):
        self.with_limit(4)
        user_limit = UserLimit.for_request(SimpleNamespace(tenant=self.negocio))
        self.assertEqual((user_limit.limit, user_limit.active_count), (4, 1))

    def test_of_counts_from_the_public_schema(self):
        self.member("ana")
        self.with_limit(5)
        connection.set_schema_to_public()
        user_limit = UserLimit.of(self.negocio)
        self.assertEqual(user_limit.usage_label, "2 / 5")
        self.assertEqual(connection.schema_name, "public")

    def test_of_returns_none_without_schema(self):
        connection.set_schema_to_public()
        self.assertIsNone(UserLimit.of(Negocio(schema_name="sin_esquema")))

    def test_lock_rereads_the_limit_and_the_count(self):
        user_limit = self.with_limit(1)
        self.assertEqual(user_limit.active_count, 1)
        Negocio.objects.filter(pk=self.negocio.pk).update(limite_usuarios=2)
        self.member("ana")
        with transaction.atomic():
            user_limit.lock()
            self.assertEqual((user_limit.limit, user_limit.active_count), (2, 2))
