from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.test.runner import DiscoverRunner
from django.test.utils import override_settings, setup_databases
from django_tenants.utils import schema_exists

TEMPLATE_SCHEMA = "plantilla_pruebas"


class FastTestRunner(DiscoverRunner):
    test_settings = override_settings(
        PASSWORD_HASHERS=["tests.hashers.FastPBKDF2PasswordHasher"],
        TENANT_CREATION_FAKES_MIGRATIONS=True,
        TENANT_BASE_SCHEMA=TEMPLATE_SCHEMA,
        WHITENOISE_AUTOREFRESH=True,
    )

    def __init__(self, *args, parallel=0, pdb=False, **kwargs):
        super().__init__(*args, parallel=0 if pdb else parallel, pdb=pdb, **kwargs)

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)
        parser.set_defaults(parallel="auto")

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        self.test_settings.enable()

    def teardown_test_environment(self, **kwargs):
        self.test_settings.disable()
        super().teardown_test_environment(**kwargs)

    def setup_databases(self, **kwargs):
        if settings.DATABASE_TEST_HOST:
            connection.close()
            connection.settings_dict["HOST"] = settings.DATABASE_TEST_HOST
        old_config = setup_databases(
            self.verbosity,
            self.interactive,
            time_keeper=self.time_keeper,
            keepdb=self.keepdb,
            debug_sql=self.debug_sql,
            parallel=0,
            **kwargs,
        )
        with self.time_keeper.timed(f"  Migrating '{TEMPLATE_SCHEMA}'"):
            self.migrate_template_schema()
        if self.parallel > 1:
            for index in range(self.parallel):
                with self.time_keeper.timed(f"  Cloning '{connection.alias}'"):
                    connection.creation.clone_test_db(
                        suffix=str(index + 1),
                        verbosity=self.verbosity,
                        keepdb=self.keepdb,
                    )
        return old_config

    def migrate_template_schema(self):
        connection.set_schema_to_public()
        if not schema_exists(TEMPLATE_SCHEMA):
            with connection.cursor() as cursor:
                cursor.execute(f'CREATE SCHEMA "{TEMPLATE_SCHEMA}"')
        call_command(
            "migrate_schemas",
            tenant=True,
            schema_name=TEMPLATE_SCHEMA,
            interactive=False,
            verbosity=0,
        )
        connection.set_schema_to_public()
