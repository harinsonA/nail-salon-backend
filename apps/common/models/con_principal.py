from django.db import models, transaction


class ConPrincipal(models.Model):
    campo_dueno = None

    es_principal = models.BooleanField(default=False)

    class Meta:
        abstract = True

    @staticmethod
    def restriccion_principal(campo_dueno):
        return models.UniqueConstraint(
            fields=[campo_dueno],
            condition=models.Q(es_principal=True),
            name="%(app_label)s_%(class)s_un_principal",
        )

    def save(self, *args, **kwargs):
        with transaction.atomic(using=kwargs.get("using")):
            if self.es_principal:
                self._desmarcar_otros_principales()
            super().save(*args, **kwargs)

    def _desmarcar_otros_principales(self):
        campo = f"{self.campo_dueno}_id"
        otros = (
            type(self)
            ._default_manager.select_for_update()
            .filter(**{campo: getattr(self, campo)}, es_principal=True)
            .exclude(pk=self.pk)
        )
        for otro in otros:
            otro.es_principal = False
            otro.save()
