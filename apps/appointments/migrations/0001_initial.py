from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('services', '0001_initial'),
        ('clients', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Cita',
            fields=[
                ('cita_id', models.AutoField(primary_key=True, serialize=False)),
                ('fecha_hora_cita', models.DateTimeField()),
                ('estado_cita', models.CharField(choices=[('PENDIENTE', 'Pendiente'), ('CONFIRMADA', 'Confirmada'), ('CANCELADA', 'Cancelada'), ('COMPLETADA', 'Completada')], default='PENDIENTE', max_length=20)),
                ('observaciones', models.TextField(blank=True, null=True)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True)),
                ('cliente', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='citas', to='clients.cliente')),
                ('creado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Cita',
                'verbose_name_plural': 'Citas',
                'db_table': 'citas',
                'ordering': ['-fecha_hora_cita'],
            },
        ),
        migrations.CreateModel(
            name='DetalleCita',
            fields=[
                ('detalle_cita_id', models.AutoField(primary_key=True, serialize=False)),
                ('precio_acordado', models.DecimalField(decimal_places=2, max_digits=10)),
                ('cantidad_servicios', models.PositiveIntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)])),
                ('notas_detalle', models.TextField(blank=True, null=True)),
                ('descuento', models.DecimalField(decimal_places=2, default=0, max_digits=5, validators=[django.core.validators.MinValueValidator(0)])),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('cita', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='detalles', to='appointments.cita')),
                ('servicio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='services.servicio')),
            ],
            options={
                'verbose_name': 'Detalle de Cita',
                'verbose_name_plural': 'Detalles de Citas',
                'db_table': 'detalle_cita',
                'unique_together': {('cita', 'servicio')},
            },
        ),
    ]
