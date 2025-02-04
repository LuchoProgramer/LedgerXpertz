from django.urls import path
from . import views


urlpatterns = [
    path('ventas_por_turno/', views.reporte_ventas_por_turno, name='reporte_ventas_por_turno'),
    path('seleccionar_turno/', views.seleccionar_turno_por_fechas, name='seleccionar_turno_por_fechas'),
    path('usuarios/', views.listar_usuarios, name='listar_usuarios'),  # Cambiado de empleados a usuarios
    path('buscar_turno/', views.buscar_turno_por_id, name='buscar_turno_por_id'),
    path('filtro_turnos/', views.seleccionar_turno_detallado, name='seleccionar_turno_detallado'),
    path('reporte-ventas/', views.reporte_ventas, name='reporte_ventas'),
    path('reporte-ventas-filtrado/', views.reporte_ventas_filtrado, name='reporte_ventas_filtrado'),  # Nueva URL
]
