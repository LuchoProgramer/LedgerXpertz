# facturacion/urls.py
from django.urls import path
from . import views

app_name = 'facturacion'  # Usamos el namespace 'facturacion'

urlpatterns = [
    path('impuestos/', views.lista_impuestos, name='lista_impuestos'),
    path('impuestos/crear/', views.crear_impuesto, name='crear_impuesto'),
    path("generar-cotizacion/<int:cotizacion_id>/", views.generar_pdf_cotizacion_view, name="generar_pdf_cotizacion"),
    path("generar-factura/", views.generar_factura, name="generar_factura"),
    path("crear-cliente/", views.crear_cliente_ajax, name="crear_cliente_ajax"),
]
