from django.db import models
from empresas.models import Empresa
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from facturacion.models import Impuesto


class Sucursal(models.Model):
    nombre = models.CharField(max_length=200, unique=True)
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='sucursales', db_constraint=False)
    direccion = models.TextField()
    telefono = models.CharField(max_length=20)
    codigo_establecimiento = models.CharField(max_length=3, blank=True, null=True)
    punto_emision = models.CharField(max_length=3, blank=True, null=True)
    es_matriz = models.BooleanField(default=False)
    secuencial_actual = models.CharField(max_length=9, default="000000000")
    usuarios = models.ManyToManyField(User, related_name='sucursales')

    class Meta:
        unique_together = ('codigo_establecimiento', 'punto_emision')
        indexes = [
            models.Index(fields=['empresa']),
            models.Index(fields=['codigo_establecimiento', 'punto_emision']),
        ]

    def __str__(self):
        return f"{self.nombre} - {self.direccion}"

    def clean(self):
        """Validaciones personalizadas antes de guardar."""
        if not self.empresa:
            raise ValidationError("La sucursal debe pertenecer a una empresa.")

        # Validar que solo haya una sucursal marcada como matriz por empresa
        if self.es_matriz and Sucursal.objects.filter(empresa=self.empresa, es_matriz=True).exclude(pk=self.pk).exists():
            raise ValidationError('Ya existe una sucursal marcada como matriz en esta empresa.')

        # Si hay código de establecimiento o punto de emisión, el RUC debe estar presente
        if (self.codigo_establecimiento or self.punto_emision) and not getattr(self.empresa, 'ruc', None):
            raise ValidationError('El RUC es obligatorio si se especifica código de establecimiento o punto de emisión.')

        # Validar que el RUC tenga exactamente 13 dígitos
        if self.empresa and self.empresa.ruc and len(self.empresa.ruc) != 13:
            raise ValidationError('El RUC debe tener exactamente 13 dígitos.')

    def incrementar_secuencial(self):
        """Incrementa el secuencial actual asegurando que tenga 9 dígitos."""
        nuevo_secuencial = str(int(self.secuencial_actual) + 1).zfill(9)
        self.secuencial_actual = nuevo_secuencial
        self.save()

    def save(self, *args, **kwargs):
        """Método save personalizado para garantizar validaciones antes de guardar."""
        self.full_clean()  # Ejecutar validaciones de `clean()`
        super().save(*args, **kwargs)


class Categoria(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='categorias', db_constraint=False) # Relacion con Empresa
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = ('empresa', 'nombre') #Unique together para que sea unico por empresa
    def __str__(self):
        return self.nombre
    
class Producto(models.Model):
    TIPO_CHOICES = (
        ('producto', 'Producto'),
        ('servicio', 'Servicio'),
    )
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='productos', db_constraint=False)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='producto')
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(null=True, blank=True)
    unidad_medida = models.CharField(max_length=50, null=True, blank=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True, related_name='productos')
    sucursales = models.ManyToManyField(Sucursal, blank=True, related_name="productos")
    codigo_producto = models.CharField(max_length=50, null=True, blank=True)
    impuesto = models.ForeignKey('facturacion.Impuesto', on_delete=models.CASCADE, null=True, blank=True, related_name='productos')
    image = models.ImageField(upload_to='productos/', null=True, blank=True)
    stock_minimo = models.IntegerField(default=0)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('empresa', 'nombre')
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'


    def __str__(self):
        return self.nombre
    
    def obtener_valor_base_iva(self, presentacion):
        if self.impuesto and self.impuesto.porcentaje > 0:
            valor_base = (presentacion.precio / (1 + self.impuesto.porcentaje / 100)).quantize(Decimal('0.01'))
            valor_iva = (presentacion.precio - valor_base).quantize(Decimal('0.01'))
            return valor_base, valor_iva
        return presentacion.precio.quantize(Decimal('0.01')), Decimal('0.00')

    def calcular_precio_final(self, presentacion):
        return presentacion.precio

    def save(self, *args, **kwargs):
        if not self.impuesto:
            self.impuesto = Impuesto.objects.get(porcentaje=15.0)
        super().save(*args, **kwargs)

    def clean(self):
        pass

class Presentacion(models.Model):
    producto = models.ForeignKey('Producto', on_delete=models.CASCADE, related_name='presentaciones')
    nombre_presentacion = models.CharField(max_length=50)
    cantidad = models.PositiveIntegerField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    porcentaje_adicional = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Porcentaje adicional a aplicar al precio (0-100)."
    )
    sucursal = models.ForeignKey('Sucursal', on_delete=models.CASCADE, related_name='presentaciones')

    class Meta:
        verbose_name = 'Presentación'
        verbose_name_plural = 'Presentaciones'

    def __str__(self):
        return f"{self.nombre_presentacion} - {self.producto.nombre} - {self.sucursal.nombre}"

    def clean(self):
        if self.precio <= 0:
            raise ValidationError("El precio debe ser mayor que cero.")
        if self.cantidad <= 0:
            raise ValidationError("La cantidad debe ser mayor que cero.")

    def calcular_precio_con_porcentaje(self):
        precio_final = self.precio * (1 + (self.porcentaje_adicional / 100))
        return precio_final.quantize(Decimal('0.01'))

    def save(self, *args, **kwargs):
        # Aquí, como ya asociamos producto y sucursal con el tenant, podemos agregar una verificación adicional.
        if self.producto.empresa != self.sucursal.empresa:
            raise ValidationError("La sucursal y el producto deben pertenecer a la misma empresa.")
        super().save(*args, **kwargs)