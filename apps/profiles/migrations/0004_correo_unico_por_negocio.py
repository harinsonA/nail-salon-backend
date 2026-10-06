from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("profiles", "0003_perfiles_con_rol_telefonos_y_direcciones"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "UPDATE auth_user SET email = LOWER(TRIM(email)) WHERE email <> LOWER(TRIM(email));"
                "CREATE UNIQUE INDEX auth_user_correo_unico ON auth_user (LOWER(email)) WHERE email <> '';"
            ),
            reverse_sql="DROP INDEX IF EXISTS auth_user_correo_unico;",
        ),
    ]
