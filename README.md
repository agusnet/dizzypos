# DizzyPOS

Sistema de punto de venta e inventario desarrollado con Django y Bootstrap 5.

## Características

- **Punto de Venta (Ventas)**:
  - Vista en cuadrícula de productos con buscador en tiempo real y filtro por categorías.
  - Validación de stock estricta (no permite vender productos sin stock ni superar la existencia).
  - Carrito de venta, cálculo de total y descuento.
  - Inserción de pago en efectivo y cálculo instantáneo de cambio.
  - Registro de venta en la tabla `sell` y partidas en `operation` (`operation_type_id=2`).
  - Vista e impresión de ticket individual y descarga en PDF.
- **Inventario y Compras**:
  - Control de existencias actuales (entradas menos salidas) y alertas de stock bajo o agotado.
  - Punto de compra en cuadrícula con costos de adquisición y selección de proveedor.
  - Registro de compras en la tabla `sell` y partidas en `operation` (`operation_type_id=1`).
  - Historial de compras con comprobante de entrada individual y descarga en PDF.
- **Dashboard**:
  - Resumen de ventas e ingresos del día.
  - Gráfica diaria de ventas de los últimos 30 días con Chart.js.
  - Alertas de productos en stock mínimo o agotados.
  - Visualización adaptada según el rol del usuario.
- **Roles y Permisos de Usuario**:
  - **Administrador (`kind=1`)**: Acceso completo a todos los módulos, reportes y configuración.
  - **Vendedor (`kind=2`)**: Acceso exclusivo al punto de venta, ventas del día en el dashboard, consulta de productos y directorio de clientes (puede agregar clientes, sin editar ni eliminar).
- **Catálogos**:
  - Administración de productos, categorías, clientes y proveedores.
- **Reportes con exportación a PDF**:
  - Reporte de ventas por rango de fechas.
  - Reporte de compras por rango de fechas.
  - Reporte de movimientos de inventario (entradas y salidas) por rango de fechas.
- **Administración y Configuración**:
  - Módulo de usuarios (creación, edición y asignación de roles).
  - Parámetros del negocio guardados en la tabla `configuration` (nombre de empresa, teléfono, dirección y mensaje al pie del ticket).

## Estructura de Base de Datos (basada en schema.sql)

- `category`: Categorías de productos.
- `product`: Productos con precio de compra (`price_in`), precio de venta (`price_out`) y existencia mínima (`inventary_min`).
- `person`: Clientes (`kind=1`) y Proveedores (`kind=2`).
- `operation_type`: Tipos de movimiento (`1` para entrada/compras, `2` para salida/ventas).
- `box`: Cajas registradoras.
- `sell`: Encabezado de transacciones de venta o compra.
- `operation`: Detalle de productos y cantidades asociadas a cada transacción.
- `configuration`: Parámetros del sistema y datos del ticket.

## Instalación y Puesta en Marcha

1. Crear y activar el entorno virtual:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

3. Aplicar las migraciones a la base de datos:
   ```bash
   python manage.py migrate
   ```

4. Cargar datos iniciales de prueba y usuarios predeterminados:
   ```bash
   python manage.py init_pos_data
   ```
   *Usuarios creados:*
   - **Administrador:** Usuario: `admin` | Contraseña: `admin123`
   - **Vendedor:** Usuario: `vendedor` | Contraseña: `vendedor123`

5. Iniciar el servidor de desarrollo:
   ```bash
   python manage.py runserver
   ```
   Abrir en el navegador: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

## Pruebas Automatizadas

Para ejecutar las pruebas del sistema:
```bash
python manage.py test pos
```
