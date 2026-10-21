from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum


class Category(models.Model):
    name = models.CharField(max_length=50, verbose_name="Nombre")
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    image = models.ImageField(upload_to='categories/', blank=True, null=True, verbose_name="Imagen")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")

    class Meta:
        db_table = 'category'
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    barcode = models.CharField(max_length=50, blank=True, null=True, verbose_name="Código de barra")
    name = models.CharField(max_length=50, verbose_name="Nombre")
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    inventary_min = models.IntegerField(default=10, verbose_name="Mínimo en inventario")
    price_in = models.FloatField(default=0.0, verbose_name="Precio de compra")
    price_out = models.FloatField(default=0.0, verbose_name="Precio de venta")
    unit = models.CharField(max_length=255, blank=True, null=True, verbose_name="Unidad")
    presentation = models.CharField(max_length=255, blank=True, null=True, verbose_name="Presentación")
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name="Imagen")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Usuario")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Categoría")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")

    class Meta:
        db_table = 'product'
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def current_stock(self):
        entries = Operation.objects.filter(product=self, operation_type_id=1).aggregate(total=Sum('q'))['total'] or 0
        exits = Operation.objects.filter(product=self, operation_type_id=2).aggregate(total=Sum('q'))['total'] or 0
        return entries - exits

    @property
    def is_low_stock(self):
        return self.current_stock <= self.inventary_min


class Person(models.Model):
    KIND_CLIENT = 1
    KIND_PROVIDER = 2
    KIND_CHOICES = (
        (KIND_CLIENT, 'Cliente'),
        (KIND_PROVIDER, 'Proveedor'),
    )

    name = models.CharField(max_length=255, verbose_name="Nombre")
    lastname = models.CharField(max_length=50, blank=True, null=True, verbose_name="Apellido")
    company = models.CharField(max_length=50, blank=True, null=True, verbose_name="Empresa")
    address1 = models.CharField(max_length=50, blank=True, null=True, verbose_name="Dirección 1")
    address2 = models.CharField(max_length=50, blank=True, null=True, verbose_name="Dirección 2")
    phone1 = models.CharField(max_length=50, blank=True, null=True, verbose_name="Teléfono 1")
    phone2 = models.CharField(max_length=50, blank=True, null=True, verbose_name="Teléfono 2")
    email1 = models.CharField(max_length=50, blank=True, null=True, verbose_name="Correo 1")
    email2 = models.CharField(max_length=50, blank=True, null=True, verbose_name="Correo 2")
    image = models.ImageField(upload_to='persons/', blank=True, null=True, verbose_name="Imagen")
    kind = models.IntegerField(choices=KIND_CHOICES, default=KIND_CLIENT, verbose_name="Tipo")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")

    class Meta:
        db_table = 'person'
        verbose_name = 'Persona'
        verbose_name_plural = 'Personas'
        ordering = ['name']

    def __str__(self):
        full = f"{self.name} {self.lastname or ''}".strip()
        if self.company:
            return f"{full} ({self.company})"
        return full

    @property
    def full_name(self):
        return f"{self.name} {self.lastname or ''}".strip()


class OperationType(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=50, verbose_name="Nombre")

    class Meta:
        db_table = 'operation_type'
        verbose_name = 'Tipo de operación'
        verbose_name_plural = 'Tipos de operaciones'

    def __str__(self):
        return self.name


class Box(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")

    class Meta:
        db_table = 'box'
        verbose_name = 'Caja'
        verbose_name_plural = 'Cajas'

    def __str__(self):
        return f"Caja #{self.id}"


class Sell(models.Model):
    person = models.ForeignKey(Person, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Cliente / Proveedor")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Usuario")
    operation_type = models.ForeignKey(OperationType, on_delete=models.CASCADE, default=2, verbose_name="Tipo")
    box = models.ForeignKey(Box, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Caja")
    total = models.FloatField(default=0.0, verbose_name="Total")
    cash = models.FloatField(default=0.0, verbose_name="Efectivo / Pago")
    discount = models.FloatField(default=0.0, verbose_name="Descuento")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")

    class Meta:
        db_table = 'sell'
        verbose_name = 'Venta / Compra'
        verbose_name_plural = 'Ventas / Compras'
        ordering = ['-created_at']

    def __str__(self):
        tipo = "Venta" if self.operation_type_id == 2 else "Compra"
        return f"{tipo} #{self.id} - Total: ${self.total:.2f}"

    @property
    def change(self):
        if self.cash and self.cash >= self.total:
            return self.cash - self.total
        return 0.0


class Operation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Producto", related_name="operations")
    q = models.FloatField(default=0.0, verbose_name="Cantidad")
    operation_type = models.ForeignKey(OperationType, on_delete=models.CASCADE, verbose_name="Tipo")
    sell = models.ForeignKey(Sell, on_delete=models.CASCADE, verbose_name="Transacción", related_name="operations")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")

    class Meta:
        db_table = 'operation'
        verbose_name = 'Operación'
        verbose_name_plural = 'Operaciones'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.operation_type.name}: {self.q} x {self.product.name}"


class Configuration(models.Model):
    short = models.CharField(max_length=255, unique=True, verbose_name="Clave")
    name = models.CharField(max_length=255, unique=True, verbose_name="Nombre")
    kind = models.IntegerField(default=2, verbose_name="Tipo")
    val = models.CharField(max_length=255, verbose_name="Valor")

    class Meta:
        db_table = 'configuration'
        verbose_name = 'Configuración'
        verbose_name_plural = 'Configuraciones'

    def __str__(self):
        return f"{self.name} = {self.val}"
