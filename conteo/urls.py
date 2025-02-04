
from django.urls import path
from . import views

urlpatterns = [
    path('registrar/', views.registrar_conteo, name='registrar_conteo'),
    path('exitoso/', views.conteo_exitoso, name='conteo_exitoso'),
]