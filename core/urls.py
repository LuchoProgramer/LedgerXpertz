# core/urls.py
from django.urls import path
from . import views

app_name = 'core'  # Esto es necesario para que el namespace funcione correctamente

urlpatterns = [
    
    # Sucursales
    path('sucursales/', views.lista_sucursales, name='lista_sucursales'),
    path('sucursales/crear/', views.crear_sucursal, name='crear_sucursal'),
    path('sucursales/editar/<int:sucursal_id>/', views.editar_sucursal, name='editar_sucursal'),
    path('sucursales/eliminar/<int:sucursal_id>/', views.eliminar_sucursal, name='eliminar_sucursal'),
    path('sucursales/<int:sucursal_id>/', views.detalle_sucursal, name='detalle_sucursal'),
    
    # Productos
    path('productos/', views.lista_productos, name='lista_productos'),
    path('productos/crear/', views.agregar_producto, name='agregar_producto'),
    path('productos/editar/<int:producto_id>/', views.editar_producto, name='editar_producto'),
    path('productos/<int:producto_id>/', views.ver_producto, name='ver_producto'),
    path('productos/eliminar/<int:producto_id>/', views.eliminar_producto, name='eliminar_producto'),
    path('sin-sucursal/', views.sin_sucursal, name='sin_sucursal'),
    
    # Categorías
    path('categorias/', views.lista_categorias, name='lista_categorias'),
    path('categorias/crear/', views.agregar_categoria, name='agregar_categoria'),
    
    # Presentaciones
    path('productos/<int:producto_id>/agregar_presentaciones/', views.agregar_presentaciones_multiples, name='agregar_presentaciones_multiples'),
    path('presentaciones/eliminar/<int:presentacion_id>/', views.eliminar_presentacion, name='eliminar_presentacion'),
    
    # Productos por categoría (si es necesario)
    path('categorias/<int:categoria_id>/productos/', views.productos_por_categoria, name='productos_por_categoria'),
]
