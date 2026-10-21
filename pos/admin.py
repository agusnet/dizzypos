from django.contrib import admin
from .models import Category, Product, Person, OperationType, Box, Sell, Operation, Configuration


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at')
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'barcode', 'category', 'price_in', 'price_out', 'current_stock', 'is_active')
    search_fields = ('name', 'barcode')
    list_filter = ('category', 'is_active')


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'lastname', 'company', 'phone1', 'kind', 'created_at')
    search_fields = ('name', 'lastname', 'company')
    list_filter = ('kind',)


@admin.register(OperationType)
class OperationTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')


@admin.register(Box)
class BoxAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at')


class OperationInline(admin.TabularInline):
    model = Operation
    extra = 0


@admin.register(Sell)
class SellAdmin(admin.ModelAdmin):
    list_display = ('id', 'operation_type', 'person', 'total', 'cash', 'discount', 'user', 'created_at')
    list_filter = ('operation_type', 'created_at')
    inlines = [OperationInline]


@admin.register(Operation)
class OperationAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'q', 'operation_type', 'sell', 'created_at')
    list_filter = ('operation_type', 'created_at')


@admin.register(Configuration)
class ConfigurationAdmin(admin.ModelAdmin):
    list_display = ('short', 'name', 'kind', 'val')
