# models.py
from django.db import models
from empresas.models import Empresa
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator


class Impuesto(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="impuestos", db_constraint=False)
    codigo_impuesto = models.CharField(max_length=2)
    nombre = models.CharField(max_length=100)
    porcentaje = models.DecimalField(max_digits=5, decimal_places=2)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.nombre} - {self.porcentaje}%'

    def save(self, *args, **kwargs):
        if self.activo and not kwargs.pop('skip_update', False):
            # Desactiva otros impuestos antes de guardar este como activo
            Impuesto.objects.filter(empresa=self.empresa, activo=True).update(activo=False)
        super(Impuesto, self).save(*args, **kwargs)

        impuestos_activos = Impuesto.objects.filter(empresa=self.empresa, activo=True)
        print(f"Impuestos activos después de guardar: {[impuesto.nombre for impuesto in impuestos_activos]}")


class Pago(models.Model):
    # Definir los métodos de pago según el SRI
    METODOS_PAGO_SRI = [
        ('01', 'Sin utilización del sistema financiero'),
        ('15', 'Compensación de deudas'),
        ('16', 'Tarjeta de débito'),
        ('17', 'Dinero electrónico'),
        ('18', 'Tarjeta prepago'),
        ('19', 'Tarjeta de crédito'),
        ('20', 'Otros con utilización del sistema financiero'),
        ('21', 'Endoso de títulos'),
    ]

    factura = models.ForeignKey('facturacion.Factura', on_delete=models.CASCADE, related_name="pagos")
    codigo_sri = models.CharField(max_length=2, choices=METODOS_PAGO_SRI, default='01', help_text="Código del método de pago según el SRI")
    descripcion = models.CharField(max_length=100, help_text="Descripción del método de pago", default='Sin descripción')
    total = models.DecimalField(max_digits=10, decimal_places=2, help_text="Monto total del pago", default=0.00)
    plazo = models.IntegerField(null=True, blank=True, help_text="Plazo de pago en días, si aplica", default=0)
    unidad_tiempo = models.CharField(max_length=20, null=True, blank=True, help_text="Unidad de tiempo para el plazo, ej. días, meses", default='días')
    fecha_pago = models.DateTimeField(auto_now_add=True)  # Mantener como en el modelo anterior

    def __str__(self):
        return f"{self.descripcion} - {self.total} USD"



class Cliente(models.Model):
    TIPO_IDENTIFICACION_OPCIONES = [
        ('04', 'RUC'),
        ('05', 'Cédula'),
        ('06', 'Pasaporte'),
        ('07', 'Consumidor Final'),
    ]

    identificacion = models.CharField(max_length=13, unique=True, validators=[
        RegexValidator(regex='^\d{10}|\d{13}$', message='La identificación debe tener 10 dígitos (cédula) o 13 dígitos (RUC).')
    ])
    tipo_identificacion = models.CharField(max_length=2, choices=TIPO_IDENTIFICACION_OPCIONES)
    razon_social = models.CharField(max_length=200)
    direccion = models.CharField(max_length=300, null=True, blank=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    obligado_contabilidad = models.BooleanField(default=False)

    def clean(self):
        # Validar la identificación según el tipo de identificación
        if self.tipo_identificacion == '04' and len(self.identificacion) != 13:
            raise ValidationError('El RUC debe tener 13 dígitos.')
        if self.tipo_identificacion == '05' and len(self.identificacion) != 10:
            raise ValidationError('La cédula debe tener 10 dígitos.')
        if self.tipo_identificacion == '07' and self.identificacion != '9999999999':
            raise ValidationError('La identificación para Consumidor Final debe ser "9999999999".')

        super(Cliente, self).clean()

    def __str__(self):
        return f'{self.razon_social} ({self.identificacion})'


def ruta_factura(instance, filename):
    # Guardar todas las facturas directamente en la carpeta 'media'
    return filename  # Solo devolvemos el nombre del archivo, sin crear subcarpetas



class Factura(models.Model):
    ESTADOS_FACTURA = [
        ('EN_PROCESO', 'En Proceso'),
        ('AUTORIZADA', 'Autorizada'),
        ('RECHAZADA', 'Rechazada'),
    ]

    ESTADOS_PAGO = [
        ('PENDIENTE', 'Pendiente'),
        ('PAGADO_PARCIAL', 'Pagado Parcialmente'),
        ('PAGADO', 'Pagado'),
    ]

    TIPO_COMPROBANTE_OPCIONES = [
        ('01', 'Factura'),
        ('03', 'Liquidación de compra de bienes y prestación de servicios'),
        ('04', 'Nota de crédito'),
        ('05', 'Nota de débito'),
        ('06', 'Guía de remisión'),
        ('07', 'Comprobante de retención'),
    ]

    sucursal = models.ForeignKey('core.Sucursal', on_delete=models.CASCADE)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)  # Relación con Empresa (razón social)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    usuario = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    fecha_emision = models.DateTimeField(auto_now_add=True)
    numero_autorizacion = models.CharField(max_length=49, unique=True)
    clave_acceso = models.CharField(max_length=49, unique=True, null=True, blank=True)
    tipo_comprobante = models.CharField(max_length=2, choices=TIPO_COMPROBANTE_OPCIONES, default='01')
    contribuyente_especial = models.CharField(max_length=5, null=True, blank=True)
    obligado_contabilidad = models.BooleanField(default=False)
    moneda = models.CharField(max_length=10, default='DOLAR')
    total_sin_impuestos = models.DecimalField(max_digits=10, decimal_places=2)
    total_con_impuestos = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADOS_FACTURA, default='EN_PROCESO')
    estado_pago = models.CharField(max_length=20, choices=ESTADOS_PAGO, default='PENDIENTE')
    valor_iva = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    registroturno = models.ForeignKey('RegistroTurnos.RegistroTurno', on_delete=models.CASCADE, null=True, blank=True)
    archivo_pdf = models.FileField(upload_to=ruta_factura, null=True, blank=True)
    es_cotizacion = models.BooleanField(default=False)

    class Meta:
        unique_together = ('sucursal', 'numero_autorizacion')

    def calcular_total_pagado(self):
        return sum(pago.total for pago in self.pagos.all())

    def actualizar_estado_pago(self):
        total_pagado = self.calcular_total_pagado()
        if total_pagado >= self.total_con_impuestos:
            self.estado_pago = 'PAGADO'
        elif total_pagado > 0:
            self.estado_pago = 'PAGADO_PARCIAL'
        else:
            self.estado_pago = 'PENDIENTE'
        self.save()

    def clean(self):
        # Aquí ya no es necesario verificar la razón social, porque ahora está asociada con la empresa
        if not self.cliente or not self.cliente.razon_social:
            self.cliente = Cliente.objects.get_or_create(
                identificacion="9999999999",
                defaults={
                    'tipo_identificacion': '07',
                    'razon_social': 'Consumidor Final',
                }
            )[0]
        super(Factura, self).clean()

    def __str__(self):
        return f'Factura {self.numero_autorizacion} para {self.cliente.razon_social}'

    @property
    def razon_social(self):
        """
        Método para acceder a la razón social desde el modelo Empresa (tenant).
        """
        return self.empresa.razon_social



class DetalleFactura(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="detalles_factura", db_constraint=False)
    factura = models.ForeignKey('facturacion.Factura', on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey('core.Producto', on_delete=models.CASCADE)
    presentacion = models.ForeignKey('core.Presentacion', on_delete=models.CASCADE)  # Relación con Presentacion
    codigo_principal = models.CharField(max_length=20, null=True, blank=True)  # Código único del producto
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    valor_iva = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        unique_together = ('empresa', 'factura', 'producto')

    def clean(self):
        """
        Validaciones de integridad para asegurar que los datos coincidan con la lógica de negocio.
        """
        # Debugging
        print(f"Cantidad: {self.cantidad}, Precio Unitario: {self.precio_unitario}, "
              f"Subtotal esperado: {(self.cantidad * self.precio_unitario) - self.descuento}, "
              f"Subtotal actual: {self.subtotal}, Descuento: {self.descuento}")

        # Validación de cantidad
        if self.cantidad <= 0:
            raise ValidationError("La cantidad debe ser mayor que cero.")
        
        # Validación de precio unitario
        if self.precio_unitario <= 0:
            raise ValidationError("El precio unitario debe ser mayor que cero.")
        
        # Cálculo y validación de subtotal
        subtotal_calculado = (self.cantidad * self.precio_unitario) - self.descuento
        if self.subtotal != subtotal_calculado:
            raise ValidationError(f"El subtotal no es correcto. Debe ser igual a (cantidad * precio unitario) - descuento. Subtotal esperado: {subtotal_calculado}")
        
        # Validación del total
        if self.total != self.subtotal + self.valor_iva:
            raise ValidationError("El total debe ser igual al subtotal más el IVA.")

        super(DetalleFactura, self).clean()



class Cotizacion(models.Model):
    ESTADOS_COTIZACION = [
        ('PENDIENTE', 'Pendiente'),
        ('ACEPTADA', 'Aceptada'),
        ('RECHAZADA', 'Rechazada'),
        ('EXPIRADA', 'Expirada'),
    ]

    sucursal = models.ForeignKey('core.Sucursal', on_delete=models.CASCADE)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)  # Relación con Empresa (razón social)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    usuario = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    fecha_emision = models.DateTimeField(auto_now_add=True)
    numero_cotizacion = models.CharField(max_length=49, unique=True)
    moneda = models.CharField(max_length=10, default='DOLAR')
    total_sin_impuestos = models.DecimalField(max_digits=10, decimal_places=2)
    total_con_impuestos = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADOS_COTIZACION, default='PENDIENTE')
    valor_iva = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    registroturno = models.ForeignKey('RegistroTurnos.RegistroTurno', on_delete=models.CASCADE, null=True, blank=True)
    archivo_pdf = models.FileField(upload_to='cotizaciones/', null=True, blank=True)

    class Meta:
        unique_together = ('sucursal', 'numero_cotizacion')

    def __str__(self):
        return f'Cotización {self.numero_cotizacion} para {self.cliente.razon_social}'

    @property
    def razon_social(self):
        """
        Método para acceder a la razón social desde el modelo Empresa (tenant).
        """
        return self.empresa.razon_social
    



class DetalleCotizacion(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="detalles_cotizacion", db_constraint=False)
    cotizacion = models.ForeignKey(Cotizacion, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey('core.Producto', on_delete=models.CASCADE)
    presentacion = models.ForeignKey('core.Presentacion', on_delete=models.CASCADE)  # Relación con Presentacion
    codigo_principal = models.CharField(max_length=20, null=True, blank=True)  # Código único del producto
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    valor_iva = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        unique_together = ('empresa', 'cotizacion', 'producto')

    def clean(self):
        """
        Validaciones de integridad para asegurar que los datos coincidan con la lógica de negocio.
        """
        # Debugging
        print(f"Cantidad: {self.cantidad}, Precio Unitario: {self.precio_unitario}, "
              f"Subtotal esperado: {(self.cantidad * self.precio_unitario) - self.descuento}, "
              f"Subtotal actual: {self.subtotal}, Descuento: {self.descuento}")

        # Validación de cantidad
        if self.cantidad <= 0:
            raise ValidationError("La cantidad debe ser mayor que cero.")
        
        # Validación de precio unitario
        if self.precio_unitario <= 0:
            raise ValidationError("El precio unitario debe ser mayor que cero.")
        
        # Cálculo y validación de subtotal
        subtotal_calculado = (self.cantidad * self.precio_unitario) - self.descuento
        if self.subtotal != subtotal_calculado:
            raise ValidationError(f"El subtotal no es correcto. Debe ser igual a (cantidad * precio unitario) - descuento. Subtotal esperado: {subtotal_calculado}")
        
        # Validación del total
        if self.total != self.subtotal + self.valor_iva:
            raise ValidationError("El total debe ser igual al subtotal más el IVA.")

        super(DetalleCotizacion, self).clean()

    def __str__(self):
        return f"Detalle Cotización {self.cotizacion.numero_cotizacion} - {self.producto.nombre}"