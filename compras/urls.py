from django.urls import path
from . import views

app_name = 'compras'  # Nombre de la aplicación para las URLs

urlpatterns = [
    path('proveedores/', views.lista_proveedores, name='lista_proveedores'),  # Lista de proveedores
    path('proveedor/crear/', views.crear_proveedor, name='crear_proveedor'),  # Crear nuevo proveedor
    path('proveedor/<int:proveedor_id>/', views.detalle_proveedor, name='detalle_proveedor'),  # Detalle de proveedor
    path('proveedor/<int:proveedor_id>/editar/', views.editar_proveedor, name='editar_proveedor'),  # Editar proveedor
    path('compras/', views.lista_compras, name='lista_compras'),  # Lista de compras
    path('compra/<int:compra_id>/', views.detalle_compra, name='detalle_compra'),  # Detalle de compra
    path("compras/nueva/", views.crear_compra_con_productos, name="crear_compra_con_productos"),
    path("compras/procesar-xml/", views.procesar_compra_xml, name="procesar_compra_xml")
]