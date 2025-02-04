from django.db import models
from django.core.validators import RegexValidator
from inventarios.models import Inventario
from core.models import Producto, Sucursal
from django_tenants.utils import tenant_context

class Proveedor(models.Model):
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    nombre = models.CharField(max_length=255)  # Razón Social
    ruc = models.CharField(
        max_length=13,
        validators=[RegexValidator(regex=r'^\d{13}$', message='El RUC debe tener exactamente 13 dígitos')],
    )  # Registro Único de Contribuyentes
    direccion = models.CharField(max_length=255)
    telefono = models.CharField(
        max_length=15, 
        null=True, 
        blank=True,
        validators=[RegexValidator(regex=r'^\+?[1-9]\d{1,14}$', message='Formato de teléfono no válido')]
    )
    email = models.EmailField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


ESTADO_CHOICES = [
    ('completada', 'Completada'),
    ('pendiente', 'Pendiente'),
    ('cancelada', 'Cancelada'),
    ('procesando', 'Procesando'),
    ('enviado', 'Enviado'),
]

class Compra(models.Model):
    sucursal = models.ForeignKey('core.Sucursal', on_delete=models.CASCADE)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True)
    numero_autorizacion = models.CharField(max_length=50, default='0000000000')
    fecha_emision = models.DateField()
    total_sin_impuestos = models.DecimalField(max_digits=10, decimal_places=2)
    total_con_impuestos = models.DecimalField(max_digits=10, decimal_places=2)
    total_descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    metodo_pago = models.CharField(max_length=50, choices=[('efectivo', 'Efectivo'), ('transferencia', 'Transferencia')], default='efectivo')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')

    def __str__(self):
        return f"Compra en {self.sucursal.nombre} el {self.fecha_emision.strftime('%Y-%m-%d')}"
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['sucursal', 'fecha_emision'], name='unique_sucursal_fecha_emision')
        ]



class DetalleCompra(models.Model):
    compra = models.ForeignKey('Compra', related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)  # Producto relacionado
    codigo_principal = models.CharField(max_length=50)  # Código principal del producto
    descripcion = models.CharField(max_length=255)  # Descripción del producto
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    total_por_producto = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    impuesto_aplicado = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # Porcentaje de impuesto
    valor_impuesto = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Valor del impuesto aplicado

    def save(self, *args, **kwargs):
        # Aquí se asegura que todo se guarda en el contexto del tenant actual
        with tenant_context(self.compra.sucursal.empresa):  # Usamos la empresa asociada a la sucursal para establecer el tenant
            # Calcular el total por producto (cantidad * precio unitario)
            self.total_por_producto = self.cantidad * self.precio_unitario

            # Si se aplica impuesto, calcular el valor del impuesto
            if self.impuesto_aplicado:
                self.valor_impuesto = (self.total_por_producto * self.impuesto_aplicado) / 100

            # Actualizar el inventario del producto relacionado
            inventario, created = Inventario.objects.get_or_create(
                producto=self.producto,
                sucursal=self.compra.sucursal,
                defaults={'cantidad': self.cantidad}
            )

            if not created:
                inventario.cantidad += self.cantidad  # Sumar la cantidad comprada al inventario existente
            inventario.save()

            # Llamar al método save de la clase padre
            super(DetalleCompra, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.cantidad} x {self.descripcion} en {self.compra.sucursal.nombre}"