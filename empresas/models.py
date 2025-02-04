from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
from django.core.validators import RegexValidator

class Empresa(TenantMixin):
    """
    Modelo para representar una empresa (razón social) en Ecuador.
    """
    # Datos básicos
    nombre_comercial = models.CharField("Nombre Comercial", max_length=255)
    razon_social = models.CharField("Razón Social", max_length=255, unique=True)
    ruc = models.CharField(
        "RUC",
        max_length=13,
        unique=True,
        validators=[
            RegexValidator(
                regex='^\d{13}$',
                message='El RUC debe tener exactamente 13 dígitos numéricos.'
            )
        ]
    )

    # Información de contacto
    direccion = models.TextField("Dirección", blank=True)
    telefono = models.CharField("Teléfono", max_length=20, blank=True)
    correo_electronico = models.EmailField("Correo Electrónico", blank=True)

    # Información fiscal
    obligado_contabilidad = models.BooleanField("Obligado a llevar contabilidad", default=False)
    tipo_contribuyente = models.CharField("Tipo de Contribuyente", max_length=50, blank=True)

    # Información adicional
    representante_legal = models.CharField("Representante Legal", max_length=255, blank=True)
    actividad_economica = models.CharField("Actividad Económica", max_length=255, blank=True)

    # Configuración de django-tenants
    auto_create_schema = True


    def __str__(self):
        return self.nombre_comercial


class Dominio(DomainMixin):
    pass  # No necesitas un campo ForeignKey aquí