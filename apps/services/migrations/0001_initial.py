from django.db import migrations, models
import utils.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Servicio',
            fields=[
                ('servicio_id', models.AutoField(primary_key=True, serialize=False)),
                ('nombre_servicio', models.CharField(max_length=200)),
                ('precio', models.DecimalField(decimal_places=2, max_digits=10, validators=[utils.validators.validate_precio_positivo])),
                ('descripcion', models.TextField()),
                ('duracion_estimada', models.DurationField(validators=[utils.validators.validate_duracion_positiva])),
                ('activo', models.BooleanField(default=True)),
                ('categoria', models.CharField(blank=True, max_length=100)),
                ('imagen', models.ImageField(blank=True, null=True, upload_to='servicios/')),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Servicio',
                'verbose_name_plural': 'Servicios',
                'db_table': 'servicios',
                'ordering': ['nombre_servicio'],
            },
        ),
    ]
