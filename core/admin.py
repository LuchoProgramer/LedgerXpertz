from django.contrib import admin
from .models import Sucursal, Categoria, Producto, Presentacion
from django.contrib.auth.models import User
from django.utils.html import format_html

# Personalización del modelo Sucursal en el admin
class SucursalAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'empresa', 'direccion', 'telefono', 'es_matriz', 'codigo_establecimiento', 'punto_emision', 'secuencial_actual')
    search_fields = ('nombre', 'empresa__nombre', 'codigo_establecimiento', 'punto_emision')
    list_filter = ('es_matriz', 'empresa')

    def save_model(self, request, obj, form, change):
        # Aquí se puede modificar alguna lógica antes de guardar, por ejemplo asignar la empresa al objeto
        super().save_model(request, obj, form, change)

# Personalización del modelo Categoria en el admin
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'empresa', 'descripcion')
    search_fields = ('nombre', 'empresa__nombre')
    list_filter = ('empresa',)

# Personalización del modelo Producto en el admin
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'empresa', 'tipo', 'categoria', 'stock_minimo', 'activo', 'created_at')
    search_fields = ('nombre', 'empresa__nombre', 'codigo_producto')
    list_filter = ('empresa', 'activo', 'tipo')

    def save_model(self, request, obj, form, change):
        if not obj.impuesto:
            # Se asigna un impuesto por defecto si no tiene ninguno
            obj.impuesto = Impuesto.objects.get(porcentaje=15.0)
        super().save_model(request, obj, form, change)

# Personalización del modelo Presentacion en el admin
class PresentacionAdmin(admin.ModelAdmin):
    list_display = ('producto', 'nombre_presentacion', 'cantidad', 'precio', 'sucursal', 'calcular_precio_con_porcentaje')
    search_fields = ('producto__nombre', 'nombre_presentacion', 'sucursal__nombre')
    list_filter = ('producto', 'sucursal')
    
    def calcular_precio_con_porcentaje(self, obj):
        return obj.calcular_precio_con_porcentaje()
    calcular_precio_con_porcentaje.admin_order_field = 'precio'
    calcular_precio_con_porcentaje.short_description = 'Precio con porcentaje'

# Registro de los modelos en el admin
admin.site.register(Sucursal, SucursalAdmin)
admin.site.register(Categoria, CategoriaAdmin)
admin.site.register(Producto, ProductoAdmin)
admin.site.register(Presentacion, PresentacionAdmin)