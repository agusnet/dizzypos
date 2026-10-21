from django.urls import path
from . import views

urlpatterns = [
    # Dashboard / Inicio POS
    path('', views.dashboard_view, name='dashboard'),

    # POS Ventas y Compras
    path('pos/venta/', views.pos_sale_view, name='pos_sale'),
    path('pos/compra/', views.pos_purchase_view, name='pos_purchase'),

    # Listados de Ventas y Compras
    path('ventas/', views.sales_list_view, name='sales_list'),
    path('compras/', views.purchases_list_view, name='purchases_list'),
    path('transaccion/<int:pk>/', views.sell_detail_view, name='sell_detail'),

    # Tickets individuales de Venta y Compra (HTML y PDF)
    path('ventas/<int:pk>/ticket/', views.ticket_sale_view, name='ticket_sale'),
    path('ventas/<int:pk>/ticket/pdf/', views.ticket_sale_pdf_view, name='ticket_sale_pdf'),
    path('compras/<int:pk>/ticket/', views.ticket_purchase_view, name='ticket_purchase'),
    path('compras/<int:pk>/ticket/pdf/', views.ticket_purchase_pdf_view, name='ticket_purchase_pdf'),

    # Reportes (Ventas, Compras, Movimientos) en pantalla y PDF
    path('reportes/ventas/', views.report_sales_view, name='report_sales'),
    path('reportes/ventas/pdf/', views.report_sales_pdf_view, name='report_sales_pdf'),
    path('reportes/compras/', views.report_purchases_view, name='report_purchases'),
    path('reportes/compras/pdf/', views.report_purchases_pdf_view, name='report_purchases_pdf'),
    path('reportes/movimientos/', views.report_movements_view, name='report_movements'),
    path('reportes/movimientos/pdf/', views.report_movements_pdf_view, name='report_movements_pdf'),

    # Inventario y Movimientos
    path('inventario/', views.inventory_list_view, name='inventory_list'),
    path('movimientos/', views.movements_list_view, name='movements_list'),

    # Catálogos: Productos
    path('productos/', views.product_list_view, name='product_list'),
    path('productos/nuevo/', views.product_create_view, name='product_create'),
    path('productos/<int:pk>/editar/', views.product_update_view, name='product_update'),
    path('productos/<int:pk>/eliminar/', views.product_delete_view, name='product_delete'),

    # Catálogos: Categorías
    path('categorias/', views.category_list_view, name='category_list'),
    path('categorias/nueva/', views.category_create_view, name='category_create'),
    path('categorias/<int:pk>/editar/', views.category_update_view, name='category_update'),
    path('categorias/<int:pk>/eliminar/', views.category_delete_view, name='category_delete'),

    # Catálogos: Clientes
    path('clientes/', views.client_list_view, name='client_list'),
    path('clientes/nuevo/', views.client_create_view, name='client_create'),
    path('clientes/<int:pk>/editar/', views.client_update_view, name='client_update'),
    path('clientes/<int:pk>/eliminar/', views.client_delete_view, name='client_delete'),

    # Catálogos: Proveedores
    path('proveedores/', views.provider_list_view, name='provider_list'),
    path('proveedores/nuevo/', views.provider_create_view, name='provider_create'),
    path('proveedores/<int:pk>/editar/', views.provider_update_view, name='provider_update'),
    path('proveedores/<int:pk>/eliminar/', views.provider_delete_view, name='provider_delete'),

    # Administración: Usuarios y Configuración
    path('usuarios/', views.user_list_view, name='user_list'),
    path('usuarios/nuevo/', views.user_create_view, name='user_create'),
    path('usuarios/<int:pk>/editar/', views.user_update_view, name='user_update'),
    path('usuarios/<int:pk>/eliminar/', views.user_delete_view, name='user_delete'),
    path('configuracion/', views.configuration_view, name='configuration_view'),
]
