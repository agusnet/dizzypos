import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from accounts.models import Profile
from pos.models import Category, Product, Person, OperationType, Box, Sell, Operation


class PosSystemTestCase(TestCase):
    def setUp(self):
        # Tipos de operación
        self.op_entrada = OperationType.objects.create(id=1, name='entrada')
        self.op_salida = OperationType.objects.create(id=2, name='salida')

        # Usuario Administrador (kind=1)
        self.admin_user = User.objects.create_user(username='admin_test', password='password123')
        self.admin_user.profile.kind = 1
        self.admin_user.profile.save()

        # Usuario Vendedor (kind=2)
        self.seller_user = User.objects.create_user(username='vendedor_test', password='password123')
        self.seller_user.profile.kind = 2
        self.seller_user.profile.save()

        # Cliente y Proveedor
        self.client_person = Person.objects.create(name='Juan', lastname='Perez', kind=Person.KIND_CLIENT)
        self.provider_person = Person.objects.create(name='Distribuidora', company='Logistica SA', kind=Person.KIND_PROVIDER)

        # Categoría y Producto
        self.category = Category.objects.create(name='Bebidas')
        self.product = Product.objects.create(
            name='Refresco 600ml',
            barcode='750123456789',
            price_in=10.0,
            price_out=18.0,
            inventary_min=5,
            category=self.category,
            user=self.admin_user
        )

        self.client = Client()
        self.client.login(username='admin_test', password='password123')

    def test_purchase_process_creates_entry(self):
        """Prueba que una compra registra en Sell con operation_type_id=1 y suma existencia en Operation"""
        payload = {
            'person_id': self.provider_person.id,
            'total': 200.0,
            'cash': 200.0,
            'discount': 0,
            'items': [
                {'id': self.product.id, 'q': 20, 'cost': 10.0}
            ]
        }
        response = self.client.post(
            reverse('pos_purchase'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertEqual(res_data['status'], 'ok')
        sell_id = res_data['sell_id']

        # Verificar Sell
        sell = Sell.objects.get(id=sell_id)
        self.assertEqual(sell.operation_type_id, 1)
        self.assertEqual(sell.total, 200.0)
        self.assertEqual(sell.person, self.provider_person)

        # Verificar Operation
        operations = Operation.objects.filter(sell=sell)
        self.assertEqual(operations.count(), 1)
        op = operations.first()
        self.assertEqual(op.operation_type_id, 1)
        self.assertEqual(op.q, 20)
        self.assertEqual(op.product, self.product)

        # Verificar stock actual del producto (debe ser 20)
        self.assertEqual(self.product.current_stock, 20)

    def test_cannot_sell_without_stock(self):
        """Prueba que NO sea posible vender productos si no tienen stock disponible"""
        self.assertEqual(self.product.current_stock, 0)

        # Intento de venta sin stock
        payload = {
            'person_id': self.client_person.id,
            'total': 18.0,
            'cash': 20.0,
            'discount': 0.0,
            'items': [
                {'id': self.product.id, 'q': 1, 'price': 18.0}
            ]
        }
        response = self.client.post(
            reverse('pos_sale'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        res_data = response.json()
        self.assertEqual(res_data['status'], 'error')
        self.assertIn("agotado", res_data['message'].lower())

        # Ahora agregamos 5 de stock y probamos vender 6
        Sell.objects.create(id=99, operation_type=self.op_entrada, total=50)
        Operation.objects.create(product=self.product, q=5, operation_type=self.op_entrada, sell_id=99)
        self.assertEqual(self.product.current_stock, 5)

        payload_exceed = {
            'person_id': self.client_person.id,
            'total': 18.0 * 6,
            'cash': 200.0,
            'discount': 0.0,
            'items': [
                {'id': self.product.id, 'q': 6, 'price': 18.0}
            ]
        }
        response_exceed = self.client.post(
            reverse('pos_sale'),
            data=json.dumps(payload_exceed),
            content_type='application/json'
        )
        self.assertEqual(response_exceed.status_code, 400)
        self.assertIn("insuficiente", response_exceed.json()['message'].lower())

    def test_sale_process_creates_exit_and_calculates_change(self):
        """Prueba que una venta registra en Sell con operation_type_id=2 y descuenta de inventario cuando hay stock"""
        # Primero compramos 10 para tener stock
        Sell.objects.create(id=100, operation_type=self.op_entrada, total=100)
        Operation.objects.create(product=self.product, q=10, operation_type=self.op_entrada, sell_id=100)
        self.assertEqual(self.product.current_stock, 10)

        # Ahora vendemos 3 productos
        payload = {
            'person_id': self.client_person.id,
            'total': 54.0,   # 3 x 18 = 54
            'cash': 100.0,   # Pagó con 100, cambio debe ser 46
            'discount': 0.0,
            'items': [
                {'id': self.product.id, 'q': 3, 'price': 18.0}
            ]
        }
        response = self.client.post(
            reverse('pos_sale'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertEqual(res_data['status'], 'ok')
        sell_id = res_data['sell_id']

        # Verificar Sell
        sell = Sell.objects.get(id=sell_id)
        self.assertEqual(sell.operation_type_id, 2)
        self.assertEqual(sell.total, 54.0)
        self.assertEqual(sell.cash, 100.0)
        self.assertEqual(sell.change, 46.0)

        # Stock restante debe ser 10 - 3 = 7
        self.assertEqual(self.product.current_stock, 7)

    def test_dashboard_chart_data(self):
        """Prueba que el dashboard genera las etiquetas y datos para la gráfica Chart.js"""
        res = self.client.get(reverse('dashboard'))
        self.assertEqual(res.status_code, 200)
        self.assertIn('chart_labels_json', res.context)
        self.assertIn('chart_data_json', res.context)
        labels = json.loads(res.context['chart_labels_json'])
        self.assertEqual(len(labels), 30)

    def test_seller_role_restrictions(self):
        """Prueba que el vendedor tiene acceso restringido según las especificaciones"""
        seller_client = Client()
        seller_client.login(username='vendedor_test', password='password123')

        # Vendedor en dashboard solo ve ventas del día
        res_dash = seller_client.get(reverse('dashboard'))
        self.assertEqual(res_dash.status_code, 200)
        self.assertTrue(res_dash.context['is_seller'])
        self.assertNotIn('chart_labels_json', res_dash.context)

        # Puede acceder a punto de venta
        res_pos = seller_client.get(reverse('pos_sale'))
        self.assertEqual(res_pos.status_code, 200)

        # Puede ver productos
        res_prod = seller_client.get(reverse('product_list'))
        self.assertEqual(res_prod.status_code, 200)

        # NO puede crear, editar o eliminar productos (redirige con mensaje)
        self.assertEqual(seller_client.get(reverse('product_create')).status_code, 302)
        self.assertEqual(seller_client.get(reverse('product_update', args=[self.product.id])).status_code, 302)
        self.assertEqual(seller_client.get(reverse('product_delete', args=[self.product.id])).status_code, 302)

        # Puede ver clientes y agregar nuevo cliente
        self.assertEqual(seller_client.get(reverse('client_list')).status_code, 200)
        self.assertEqual(seller_client.get(reverse('client_create')).status_code, 200)

        # NO puede editar ni eliminar clientes
        self.assertEqual(seller_client.get(reverse('client_update', args=[self.client_person.id])).status_code, 302)
        self.assertEqual(seller_client.get(reverse('client_delete', args=[self.client_person.id])).status_code, 302)

        # NO puede acceder a compras, inventarios, movimientos, usuarios, proveedores
        self.assertEqual(seller_client.get(reverse('pos_purchase')).status_code, 302)
        self.assertEqual(seller_client.get(reverse('purchases_list')).status_code, 302)
        self.assertEqual(seller_client.get(reverse('inventory_list')).status_code, 302)
        self.assertEqual(seller_client.get(reverse('movements_list')).status_code, 302)
        self.assertEqual(seller_client.get(reverse('user_list')).status_code, 302)
        self.assertEqual(seller_client.get(reverse('provider_list')).status_code, 302)
        self.assertEqual(seller_client.get(reverse('configuration_view')).status_code, 302)
        self.assertEqual(seller_client.get(reverse('report_sales')).status_code, 302)
        self.assertEqual(seller_client.get(reverse('report_purchases')).status_code, 302)
        self.assertEqual(seller_client.get(reverse('report_movements')).status_code, 302)

    def test_user_crud_by_admin(self):
        """Prueba creación, edición y listado de usuarios por el administrador"""
        res_list = self.client.get(reverse('user_list'))
        self.assertEqual(res_list.status_code, 200)

        post_data = {
            'username': 'nuevo_cajero',
            'first_name': 'Carlos',
            'last_name': 'Mendez',
            'email': 'carlos@tienda.com',
            'password': 'segura123Password',
            'kind': 2,
            'is_active': True,
        }
        res_create = self.client.post(reverse('user_create'), data=post_data)
        self.assertEqual(res_create.status_code, 302)

        created_user = User.objects.get(username='nuevo_cajero')
        self.assertEqual(created_user.profile.kind, 2)
        self.assertTrue(created_user.profile.is_seller)
        self.assertTrue(created_user.check_password('segura123Password'))

    def test_tickets_html_and_pdf(self):
        """Prueba la visualización y descarga en PDF de tickets de venta y compra"""
        # Crear una venta
        sale = Sell.objects.create(
            operation_type=self.op_salida,
            user=self.admin_user,
            person=self.client_person,
            total=36.0,
            cash=50.0,
            discount=0.0
        )
        Operation.objects.create(product=self.product, q=2, operation_type=self.op_salida, sell=sale)

        # Ver ticket HTML de venta
        res_sale_ticket = self.client.get(reverse('ticket_sale', args=[sale.id]))
        self.assertEqual(res_sale_ticket.status_code, 200)
        self.assertContains(res_sale_ticket, "TICKET DE VENTA")
        self.assertContains(res_sale_ticket, "¡Gracias por su compra!")

        # Descargar ticket PDF de venta
        res_sale_pdf = self.client.get(reverse('ticket_sale_pdf', args=[sale.id]))
        self.assertEqual(res_sale_pdf.status_code, 200)
        self.assertEqual(res_sale_pdf['Content-Type'], 'application/pdf')

        # Crear una compra
        purchase = Sell.objects.create(
            operation_type=self.op_entrada,
            user=self.admin_user,
            person=self.provider_person,
            total=100.0,
            cash=100.0,
            discount=0.0
        )
        Operation.objects.create(product=self.product, q=10, operation_type=self.op_entrada, sell=purchase)

        # Ver comprobante HTML de compra
        res_pur_ticket = self.client.get(reverse('ticket_purchase', args=[purchase.id]))
        self.assertEqual(res_pur_ticket.status_code, 200)
        self.assertContains(res_pur_ticket, "COMPROBANTE DE COMPRA")

        # Descargar ticket PDF de compra
        res_pur_pdf = self.client.get(reverse('ticket_purchase_pdf', args=[purchase.id]))
        self.assertEqual(res_pur_pdf.status_code, 200)
        self.assertEqual(res_pur_pdf['Content-Type'], 'application/pdf')

    def test_reports_views_and_pdfs(self):
        """Prueba las vistas de reportes y descarga en PDF para ventas, compras y movimientos"""
        # Reporte de ventas
        res_rep_sales = self.client.get(reverse('report_sales'))
        self.assertEqual(res_rep_sales.status_code, 200)
        res_rep_sales_pdf = self.client.get(reverse('report_sales_pdf'))
        self.assertEqual(res_rep_sales_pdf.status_code, 200)
        self.assertEqual(res_rep_sales_pdf['Content-Type'], 'application/pdf')

        # Reporte de compras
        res_rep_pur = self.client.get(reverse('report_purchases'))
        self.assertEqual(res_rep_pur.status_code, 200)
        res_rep_pur_pdf = self.client.get(reverse('report_purchases_pdf'))
        self.assertEqual(res_rep_pur_pdf.status_code, 200)
        self.assertEqual(res_rep_pur_pdf['Content-Type'], 'application/pdf')

        # Reporte de movimientos
        res_rep_mov = self.client.get(reverse('report_movements'))
        self.assertEqual(res_rep_mov.status_code, 200)
        res_rep_mov_pdf = self.client.get(reverse('report_movements_pdf'))
        self.assertEqual(res_rep_mov_pdf.status_code, 200)
        self.assertEqual(res_rep_mov_pdf['Content-Type'], 'application/pdf')

    def test_configuration_view(self):
        """Prueba visualización y actualización de la tabla configuration"""
        res_get = self.client.get(reverse('configuration_view'))
        self.assertEqual(res_get.status_code, 200)

        post_data = {
            'title': 'Mi Tienda POS',
            'company_name': 'Comercializadora Ejemplo',
            'company_phone': '555-987-6543',
            'company_address': 'Calle 50 #123',
            'ticket_footer': '¡Vuelva pronto, gracias por su compra!',
        }
        res_post = self.client.post(reverse('configuration_view'), data=post_data)
        self.assertEqual(res_post.status_code, 302)

        from pos.models import Configuration
        self.assertEqual(Configuration.objects.get(short='company_name').val, 'Comercializadora Ejemplo')
        self.assertEqual(Configuration.objects.get(short='ticket_footer').val, '¡Vuelva pronto, gracias por su compra!')
