from django.db import models
from django.core.exceptions import ValidationError
from django_tenants.utils import tenant_context  # Importante para multitenancy

class ConteoDiario(models.Model):
    sucursal = models.ForeignKey('core.Sucursal', on_delete=models.CASCADE)  
    usuario = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    fecha_conteo = models.DateField(auto_now_add=True)
    producto = models.ForeignKey('core.Producto', on_delete=models.CASCADE)  
    cantidad_contada = models.IntegerField()

    def __str__(self):
        return f"Conteo de {self.producto.nombre} en {self.sucursal.nombre} - {self.cantidad_contada} unidades"

    def clean(self):
        """
        Este método se utiliza para validar los datos del conteo antes de ser guardados.
        Se asegura de que las cantidades no sean negativas y de que cada producto tenga su cantidad registrada.
        """
        cleaned_data = super().clean()

        # Validamos que la cantidad no sea negativa
        if self.cantidad_contada < 0:
            raise ValidationError({'cantidad_contada': 'La cantidad no puede ser negativa.'})

        # Validamos que el conteo esté asociado con una sucursal y un producto pertenecientes al tenant actual
        with tenant_context(self.sucursal.empresa):  # Usamos el contexto del tenant (empresa)
            # Validamos que el producto esté relacionado con la empresa del tenant
            if not self.producto in self.sucursal.productos.all():
                raise ValidationError({'producto': 'El producto no está asociado con esta sucursal.'})

        return cleaned_data