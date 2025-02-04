from django.contrib import admin
from django_tenants.admin import TenantAdminMixin

from .models import Empresa, Dominio

@admin.register(Empresa)
class EmpresaAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = (
        'nombre_comercial',
        'razon_social',
        'ruc',
        'telefono',
        'correo_electronico',
        'obligado_contabilidad',
        'schema_name',  # Agregado
    )
    search_fields = ('nombre_comercial', 'razon_social', 'ruc')
    list_filter = ('obligado_contabilidad', 'tipo_contribuyente')

@admin.register(Dominio)
class DominioAdmin(admin.ModelAdmin):
    list_display = ('domain', 'tenant')
    search_fields = ('domain', 'tenant__nombre_comercial')