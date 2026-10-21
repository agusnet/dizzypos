from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from pos.models import OperationType, Configuration, Category, Product, Person, Sell, Operation


class Command(BaseCommand):
    help = "Inicializa tipos de operación, configuración básica y datos iniciales de demo"

    def handle(self, *args, **options):
        # 1. Tipos de operación obligatorios
        op_entrada, _ = OperationType.objects.get_or_create(id=1, defaults={'name': 'entrada'})
        op_salida, _ = OperationType.objects.get_or_create(id=2, defaults={'name': 'salida'})
        self.stdout.write(self.style.SUCCESS("Tipos de operación verificados (1: entrada, 2: salida)."))

        # 2. Configuración
        Configuration.objects.get_or_create(
            short="title",
            defaults={
                'name': 'Titulo del Sistema',
                'kind': 2,
                'val': 'DizzyPOS'
            }
        )
        self.stdout.write(self.style.SUCCESS("Configuración inicial verificada."))

        # 3. Usuarios por defecto (Admin y Vendedor)
        admin_user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                'email': 'admin@dizzypos.com',
                'first_name': 'Administrador',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin_user.set_password("admin123")
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("Usuario admin creado con clave: admin123"))
        if hasattr(admin_user, 'profile'):
            admin_user.profile.kind = 1
            admin_user.profile.save()

        seller_user, s_created = User.objects.get_or_create(
            username="vendedor",
            defaults={
                'email': 'vendedor@dizzypos.com',
                'first_name': 'Vendedor',
                'is_staff': False,
                'is_superuser': False,
            }
        )
        if s_created:
            seller_user.set_password("vendedor123")
            seller_user.save()
            self.stdout.write(self.style.SUCCESS("Usuario vendedor creado con clave: vendedor123"))
        if hasattr(seller_user, 'profile'):
            seller_user.profile.kind = 2
            seller_user.profile.save()

        # 4. Datos demo de categorías (de schema.sql)
        categories_data = [
            (1, 'Electrónica', 'Dispositivos y accesorios electrónicos'),
            (2, 'Papelería', 'Artículos de oficina y papelería'),
            (3, 'Abarrotes', 'Productos alimenticios y víveres'),
            (4, 'Lácteos', 'Leche, quesos y derivados lácteos'),
            (5, 'Bebidas', 'Refrescos, jugos y aguas'),
            (6, 'Limpieza', 'Productos para aseo y limpieza del hogar'),
            (7, 'Ferretería', 'Herramientas y materiales de ferretería'),
            (8, 'Ropa y Calzado', 'Prendas de vestir y calzado'),
            (9, 'Farmacia', 'Medicamentos y cuidado personal'),
            (10, 'Hogar y Jardín', 'Artículos para el hogar y jardinería'),
        ]
        for cid, name, desc in categories_data:
            Category.objects.get_or_create(id=cid, defaults={'name': name, 'description': desc})

        # 5. Clientes y proveedores de demo (de schema.sql)
        persons_data = [
            (1, 'Roberto', 'García', 'Distribuidora García', 'Av. Central 123', '555-0101', 'roberto@garcia.com', 1),
            (2, 'Patricia', 'Sánchez', 'Comercial Sánchez', 'Calle Norte 45', '555-0102', 'patricia@sanchez.com', 1),
            (3, 'Fernando', 'Romero', 'Servicios Romero', 'Calle Sur 78', '555-0103', 'fernando@romero.com', 1),
            (4, 'Claudia', 'Vargas', 'Importaciones Vargas', 'Av. Principal 500', '555-0104', 'claudia@vargas.com', 1),
            (5, 'Jorge', 'Castro', 'Mendoza & Castro', 'Calle 10 # 25', '555-0105', 'jorge@castro.com', 1),
            (11, 'Proveedor', 'Alfa', 'Proveedor Alfa S.A.', 'Industrial Park 1', '555-0201', 'contacto@alfa.com', 2),
            (12, 'Proveedor', 'Beta', 'Suministros Beta', 'Zona Industrial 4', '555-0202', 'ventas@beta.com', 2),
            (13, 'Proveedor', 'Gamma', 'Distribuidora Gamma', 'Calle Fabril 12', '555-0203', 'info@gamma.com', 2),
            (14, 'Proveedor', 'Delta', 'Delta Logística', 'Av. Comercio 888', '555-0204', 'contacto@delta.com', 2),
            (15, 'Proveedor', 'Epsilon', 'Epsilon Importaciones', 'Parque Tecnológico 3', '555-0205', 'servicio@epsilon.com', 2),
        ]
        for pid, name, lastname, company, addr, phone, email, kind in persons_data:
            Person.objects.get_or_create(
                id=pid,
                defaults={
                    'name': name,
                    'lastname': lastname,
                    'company': company,
                    'address1': addr,
                    'phone1': phone,
                    'email1': email,
                    'kind': kind,
                }
            )

        # 6. Productos demo (de schema.sql)
        products_data = [
            (1, '750100000001', 'Laptop HP 15"', 'Intel Core i5 8GB RAM 256GB SSD', 5, 450.00, 650.00, 'Pieza', 'Caja', 1),
            (2, '750100000002', 'Mouse Inalámbrico Logitech', 'Mouse óptico ergonómico USB', 10, 12.00, 25.00, 'Pieza', 'Empaque', 1),
            (3, '750100000003', 'Cuaderno Profesional 100 Hojas', 'Cuaderno de raya espiral doble', 20, 1.50, 3.50, 'Pieza', 'Paquete', 2),
            (4, '750100000004', 'Bolígrafo Gel Negro 0.7mm', 'Caja con 12 bolígrafos de gel', 15, 4.00, 8.50, 'Caja', 'Caja', 2),
            (5, '750100000005', 'Café Tostado en Grano 1kg', 'Café 100% Arábica de altura', 10, 8.00, 15.00, 'Kg', 'Bolsa', 3),
            (6, '750100000006', 'Leche Entera 1 Litro', 'Leche pasteurizada adicionada con vitaminas', 30, 0.80, 1.40, 'Litro', 'Envase', 4),
            (7, '750100000007', 'Jugo de Naranja 1L', 'Jugo 100% natural sin azúcar añadida', 25, 1.20, 2.20, 'Litro', 'Botella', 5),
            (8, '750100000008', 'Detergente Multiusos 2kg', 'Detergente en polvo biodegradable', 15, 3.50, 6.00, 'Bolsa', 'Bolsa', 6),
            (9, '750100000009', 'Juego de Destornilladores 6 pzs', 'Destornilladores de cruz y planos en acero', 5, 7.50, 14.00, 'Juego', 'Estuche', 7),
            (10, '750100000010', 'Camiseta Algodón Talla M', 'Camiseta 100% algodón cuello redondo', 10, 5.00, 11.00, 'Pieza', 'Bolsa', 8),
        ]
        for pid, barcode, name, desc, inv_min, p_in, p_out, unit, pres, cat_id in products_data:
            prod, _ = Product.objects.get_or_create(
                id=pid,
                defaults={
                    'barcode': barcode,
                    'name': name,
                    'description': desc,
                    'inventary_min': inv_min,
                    'price_in': p_in,
                    'price_out': p_out,
                    'unit': unit,
                    'presentation': pres,
                    'category_id': cat_id,
                    'user': admin_user,
                    'is_active': True,
                }
            )

        # 7. Inventario inicial de prueba si no hay operaciones
        if Operation.objects.count() == 0:
            provider = Person.objects.filter(kind=Person.KIND_PROVIDER).first()
            initial_sell = Sell.objects.create(
                id=1,
                person=provider,
                user=admin_user,
                operation_type=op_entrada,
                total=5000.0,
                cash=5000.0,
                discount=0.0
            )
            for prod in Product.objects.all():
                Operation.objects.create(
                    product=prod,
                    q=25,
                    operation_type=op_entrada,
                    sell=initial_sell
                )
            self.stdout.write(self.style.SUCCESS("Inventario inicial de 25 unidades por producto cargado."))

        self.stdout.write(self.style.SUCCESS("Datos iniciales cargados correctamente."))
