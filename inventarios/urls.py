from django.urls import path
from . import views

app_name = "inventarios"  # Define un namespace para la aplicación

urlpatterns = [
    # Seleccionar Sucursal
    path('seleccionar-sucursal/', views.seleccionar_sucursal, name='seleccionar_sucursal'),

    # Inventario
    path('inventario/<int:sucursal_id>/', views.ver_inventario, name='ver_inventario'),
    path('inventario/agregar/', views.agregar_producto_inventario, name='agregar_producto_inventario'),
    path('inventario/ajustar/<int:producto_id>/<int:sucursal_id>/', views.ajustar_inventario, name='ajustar_inventario'),

    # Transferencias
    path('transferencias/crear/', views.crear_transferencia, name='crear_transferencia'),
    path('transferencias/', views.lista_transferencias, name='lista_transferencias'),

    # Movimientos de inventario
    path('movimientos/', views.lista_movimientos_inventario, name='lista_movimientos_inventario'),

    # Agregar inventario manualmente
    path('inventario/agregar-manual/<int:sucursal_id>/', views.agregar_inventario_manual, name='agregar_inventario_manual'),

    # Cargar inventario desde Excel
    path('inventario/cargar-excel/<int:sucursal_id>/', views.cargar_inventario_excel, name='cargar_inventario_excel'),
    path('api/stock_disponible/<int:sucursal_id>/<int:producto_id>/', views.obtener_stock_disponible, name='stock_disponible'),
]