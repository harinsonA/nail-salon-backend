from django.db import migrations, models


def salon_a_negocio(apps, schema_editor):
    for modelo in ("Preference", "HistoricalPreference"):
        apps.get_model("settings", modelo).objects.filter(scope="salon").update(scope="negocio")


def negocio_a_salon(apps, schema_editor):
    for modelo in ("Preference", "HistoricalPreference"):
        apps.get_model("settings", modelo).objects.filter(scope="negocio").update(scope="salon")


class Migration(migrations.Migration):

    dependencies = [
        ("settings", "0002_historicalpreference_preference_and_more"),
    ]

    operations = [
        migrations.RenameModel(old_name="ConfiguracionSalon", new_name="ConfiguracionNegocio"),
        migrations.AlterModelTable(name="configuracionnegocio", table="configuracion_negocio"),
        migrations.AlterModelOptions(
            name="configuracionnegocio",
            options={
                "verbose_name": "Configuración del negocio",
                "verbose_name_plural": "Configuraciones del negocio",
            },
        ),
        migrations.RenameField(model_name="configuracionnegocio", old_name="nombre_salon", new_name="nombre_visible"),
        migrations.AlterField(
            model_name="configuracionnegocio",
            name="nombre_visible",
            field=models.CharField(max_length=150),
        ),
        migrations.RemoveField(model_name="configuracionnegocio", name="direccion"),
        migrations.AlterField(
            model_name="historicalpreference",
            name="scope",
            field=models.CharField(
                choices=[("user", "Usuario"), ("negocio", "Negocio")],
                default="user",
                max_length=20,
                verbose_name="Alcance",
            ),
        ),
        migrations.AlterField(
            model_name="preference",
            name="scope",
            field=models.CharField(
                choices=[("user", "Usuario"), ("negocio", "Negocio")],
                default="user",
                max_length=20,
                verbose_name="Alcance",
            ),
        ),
        migrations.RunPython(salon_a_negocio, negocio_a_salon),
    ]
