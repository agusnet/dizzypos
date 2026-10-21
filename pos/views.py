import json
import datetime
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, FileResponse
from django.db import transaction
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Sum, Q

from accounts.models import Profile
from .models import Product, Category, Person, OperationType, Box, Sell, Operation, Configuration
from .forms import ProductForm, CategoryForm, PersonForm, UserCreateForm, UserUpdateForm
from .pdf_utils import (
    get_config_dict,
    generate_sale_ticket_pdf,
    generate_purchase_ticket_pdf,
    generate_sales_report_pdf,
    generate_purchases_report_pdf,
    generate_movements_report_pdf
)


def admin_required(view_func):
    """Permite el acceso únicamente a usuarios con rol Administrador (kind=1) o superusuarios."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        profile = getattr(request.user, 'profile', None)
        if not profile or not profile.is_admin:
            messages.warning(request, "Acceso restringido: no tienes permisos de administrador.")
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


@login_required
def dashboard_view(request):
    today = timezone.now().date()
    is_seller = hasattr(request.user, 'profile') and request.user.profile.is_seller

    # Ventas de hoy
    sales_today = Sell.objects.filter(operation_type_id=2, created_at__date=today)
    total_sales_today = sales_today.aggregate(total=Sum('total'))['total'] or 0.0
    count_sales_today = sales_today.count()

    context = {
        'is_seller': is_seller,
        'total_sales_today': total_sales_today,
        'count_sales_today': count_sales_today,
    }

    if is_seller:
        # Vendedor: solo puede ver las ventas del día en el dashboard
        today_sales_list = sales_today.select_related('person', 'user').order_by('-created_at')[:10]
        context['recent_sales'] = today_sales_list
    else:
        # Administrador: métricas completas, gráfica de 30 días, compras y stock bajo
        purchases_today = Sell.objects.filter(operation_type_id=1, created_at__date=today)
        total_purchases_today = purchases_today.aggregate(total=Sum('total'))['total'] or 0.0
        count_purchases_today = purchases_today.count()

        total_products = Product.objects.filter(is_active=True).count()
        total_clients = Person.objects.filter(kind=Person.KIND_CLIENT).count()

        all_products = Product.objects.filter(is_active=True).select_related('category')
        low_stock_products = [p for p in all_products if p.is_low_stock][:10]

        recent_sales = Sell.objects.filter(operation_type_id=2).select_related('person', 'user')[:6]
        recent_purchases = Sell.objects.filter(operation_type_id=1).select_related('person', 'user')[:6]

        # Datos para la gráfica Chart.js de ventas de los últimos 30 días
        start_date = today - datetime.timedelta(days=29)
        sales_30 = Sell.objects.filter(
            operation_type_id=2,
            created_at__date__gte=start_date
        )

        daily_totals = {}
        for sale in sales_30:
            day_key = sale.created_at.strftime('%Y-%m-%d')
            daily_totals[day_key] = daily_totals.get(day_key, 0.0) + float(sale.total or 0.0)

        chart_labels = []
        chart_data = []
        for i in range(30):
            day_obj = start_date + datetime.timedelta(days=i)
            day_str = day_obj.strftime('%Y-%m-%d')
            chart_labels.append(day_obj.strftime('%d/%m'))
            chart_data.append(round(daily_totals.get(day_str, 0.0), 2))

        context.update({
            'total_purchases_today': total_purchases_today,
            'count_purchases_today': count_purchases_today,
            'total_products': total_products,
            'total_clients': total_clients,
            'low_stock_products': low_stock_products,
            'recent_sales': recent_sales,
            'recent_purchases': recent_purchases,
            'chart_labels_json': json.dumps(chart_labels),
            'chart_data_json': json.dumps(chart_data),
        })

    return render(request, 'pos/dashboard.html', context)


# ==========================================
# POS VENTAS (operation_type_id = 2)
# ==========================================
@login_required
def pos_sale_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            items = data.get('items', [])
            person_id = data.get('person_id') or None
            total = float(data.get('total', 0))
            cash = float(data.get('cash', 0))
            discount = float(data.get('discount', 0))

            if not items:
                return JsonResponse({'status': 'error', 'message': 'El carrito está vacío.'}, status=400)

            # Validar y crear la venta
            with transaction.atomic():
                # Validación de stock estricta
                for item in items:
                    product_id = item.get('id')
                    q = float(item.get('q', 1))
                    product = Product.objects.get(id=product_id)
                    current_stock = product.current_stock

                    if current_stock <= 0:
                        return JsonResponse({
                            'status': 'error',
                            'message': f'No es posible vender "{product.name}". Está agotado (Stock: 0).'
                        }, status=400)

                    if q > current_stock:
                        return JsonResponse({
                            'status': 'error',
                            'message': f'Stock insuficiente para "{product.name}". Solicitado: {q}, Disponible: {int(current_stock)}.'
                        }, status=400)

                op_type = OperationType.objects.get(id=2)
                sell = Sell.objects.create(
                    user=request.user,
                    person_id=person_id,
                    operation_type=op_type,
                    total=total,
                    cash=cash,
                    discount=discount,
                )

                for item in items:
                    product_id = item.get('id')
                    q = float(item.get('q', 1))
                    Operation.objects.create(
                        product_id=product_id,
                        q=q,
                        operation_type=op_type,
                        sell=sell,
                    )

            return JsonResponse({'status': 'ok', 'sell_id': sell.id})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    # Vista GET
    categories = Category.objects.all()
    products = Product.objects.filter(is_active=True).select_related('category')
    clients = Person.objects.filter(kind=Person.KIND_CLIENT)

    context = {
        'categories': categories,
        'products': products,
        'clients': clients,
    }
    return render(request, 'pos/pos_sale.html', context)


# ==========================================
# POS COMPRAS (operation_type_id = 1) - Solo Admin
# ==========================================
@admin_required
def pos_purchase_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            items = data.get('items', [])
            person_id = data.get('person_id') or None
            total = float(data.get('total', 0))
            cash = float(data.get('cash', total))
            discount = float(data.get('discount', 0))

            if not items:
                return JsonResponse({'status': 'error', 'message': 'El carrito está vacío.'}, status=400)

            with transaction.atomic():
                op_type = OperationType.objects.get(id=1)
                sell = Sell.objects.create(
                    user=request.user,
                    person_id=person_id,
                    operation_type=op_type,
                    total=total,
                    cash=cash,
                    discount=discount,
                )

                for item in items:
                    product_id = item.get('id')
                    q = float(item.get('q', 1))
                    Operation.objects.create(
                        product_id=product_id,
                        q=q,
                        operation_type=op_type,
                        sell=sell,
                    )

            return JsonResponse({'status': 'ok', 'sell_id': sell.id})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    # Vista GET
    categories = Category.objects.all()
    products = Product.objects.filter(is_active=True).select_related('category')
    providers = Person.objects.filter(kind=Person.KIND_PROVIDER)

    context = {
        'categories': categories,
        'products': products,
        'providers': providers,
    }
    return render(request, 'pos/pos_purchase.html', context)


# ==========================================
# HISTORIAL DE VENTAS Y COMPRAS
# ==========================================
@login_required
def sales_list_view(request):
    q = request.GET.get('q', '').strip()
    sells = Sell.objects.filter(operation_type_id=2).select_related('person', 'user').order_by('-created_at')

    # Si es vendedor, solo puede ver sus ventas o las de hoy
    if hasattr(request.user, 'profile') and request.user.profile.is_seller:
        today = timezone.now().date()
        sells = sells.filter(created_at__date=today)

    if q:
        sells = sells.filter(
            Q(id__icontains=q) |
            Q(person__name__icontains=q) |
            Q(person__lastname__icontains=q)
        )

    paginator = Paginator(sells, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'q': q,
    }
    return render(request, 'pos/sales_list.html', context)


@admin_required
def purchases_list_view(request):
    q = request.GET.get('q', '').strip()
    purchases = Sell.objects.filter(operation_type_id=1).select_related('person', 'user').order_by('-created_at')

    if q:
        purchases = purchases.filter(
            Q(id__icontains=q) |
            Q(person__name__icontains=q) |
            Q(person__company__icontains=q)
        )

    paginator = Paginator(purchases, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'q': q,
    }
    return render(request, 'pos/purchases_list.html', context)


@login_required
def sell_detail_view(request, pk):
    sell = get_object_or_404(Sell.objects.select_related('person', 'user', 'operation_type', 'box'), pk=pk)
    
    # Restricción: el vendedor no puede ver compras
    if hasattr(request.user, 'profile') and request.user.profile.is_seller and sell.operation_type_id == 1:
        messages.warning(request, "Acceso restringido: no puedes ver compras.")
        return redirect('dashboard')

    operations = sell.operations.select_related('product', 'product__category')
    is_sale = (sell.operation_type_id == 2)
    
    items = []
    calculated_subtotal = 0.0
    for op in operations:
        unit_price = op.product.price_out if is_sale else op.product.price_in
        subtotal = op.q * unit_price
        calculated_subtotal += subtotal
        items.append({
            'operation': op,
            'unit_price': unit_price,
            'subtotal': subtotal
        })

    context = {
        'sell': sell,
        'items': items,
        'calculated_subtotal': calculated_subtotal,
        'is_sale': is_sale,
    }
    return render(request, 'pos/sell_detail.html', context)


# ==========================================
# INVENTARIOS Y MOVIMIENTOS - Solo Admin
# ==========================================
@admin_required
def inventory_list_view(request):
    q = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '').strip()
    status_filter = request.GET.get('status', '').strip()

    products = Product.objects.filter(is_active=True).select_related('category')

    if q:
        products = products.filter(Q(name__icontains=q) | Q(barcode__icontains=q))
    if category_id:
        products = products.filter(category_id=category_id)

    product_list = list(products)
    if status_filter == 'low':
        product_list = [p for p in product_list if p.is_low_stock]

    paginator = Paginator(product_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.all()

    context = {
        'page_obj': page_obj,
        'categories': categories,
        'q': q,
        'selected_category': category_id,
        'selected_status': status_filter,
    }
    return render(request, 'pos/inventory_list.html', context)


@admin_required
def movements_list_view(request):
    type_id = request.GET.get('type', '').strip()
    q = request.GET.get('q', '').strip()

    operations = Operation.objects.select_related('product', 'operation_type', 'sell', 'sell__user').order_by('-created_at')

    if type_id in ['1', '2']:
        operations = operations.filter(operation_type_id=int(type_id))

    if q:
        operations = operations.filter(
            Q(product__name__icontains=q) |
            Q(product__barcode__icontains=q)
        )

    paginator = Paginator(operations, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'selected_type': type_id,
        'q': q,
    }
    return render(request, 'pos/movements_list.html', context)


# ==========================================
# PRODUCTOS (Vendedor solo puede ver)
# ==========================================
@login_required
def product_list_view(request):
    q = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '').strip()

    products = Product.objects.all().select_related('category').order_by('-id')
    if q:
        products = products.filter(Q(name__icontains=q) | Q(barcode__icontains=q))
    if category_id:
        products = products.filter(category_id=category_id)

    paginator = Paginator(products, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.all()
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'q': q,
        'selected_category': category_id,
    }
    return render(request, 'pos/product_list.html', context)


@admin_required
def product_create_view(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.user = request.user
            product.save()
            messages.success(request, f'Producto "{product.name}" creado con éxito.')
            return redirect('product_list')
    else:
        form = ProductForm()
    return render(request, 'pos/product_form.html', {'form': form, 'title': 'Nuevo producto'})


@admin_required
def product_update_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'Producto "{product.name}" actualizado con éxito.')
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'pos/product_form.html', {'form': form, 'title': 'Editar producto', 'product': product})


@admin_required
def product_delete_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        name = product.name
        product.delete()
        messages.success(request, f'Producto "{name}" eliminado.')
        return redirect('product_list')
    return render(request, 'pos/confirm_delete.html', {'object': product, 'type': 'producto', 'cancel_url': 'product_list'})


# ==========================================
# CATEGORÍAS (Solo Admin)
# ==========================================
@admin_required
def category_list_view(request):
    categories = Category.objects.all().order_by('name')
    return render(request, 'pos/category_list.html', {'categories': categories})


@admin_required
def category_create_view(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            cat = form.save()
            messages.success(request, f'Categoría "{cat.name}" creada con éxito.')
            return redirect('category_list')
    else:
        form = CategoryForm()
    return render(request, 'pos/category_form.html', {'form': form, 'title': 'Nueva categoría'})


@admin_required
def category_update_view(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Categoría "{category.name}" actualizada con éxito.')
            return redirect('category_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'pos/category_form.html', {'form': form, 'title': 'Editar categoría', 'category': category})


@admin_required
def category_delete_view(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        name = category.name
        category.delete()
        messages.success(request, f'Categoría "{name}" eliminada.')
        return redirect('category_list')
    return render(request, 'pos/confirm_delete.html', {'object': category, 'type': 'categoría', 'cancel_url': 'category_list'})


# ==========================================
# CLIENTES (Vendedor puede ver y agregar, pero no editar ni eliminar)
# ==========================================
@login_required
def client_list_view(request):
    q = request.GET.get('q', '').strip()
    clients = Person.objects.filter(kind=Person.KIND_CLIENT).order_by('-id')
    if q:
        clients = clients.filter(Q(name__icontains=q) | Q(lastname__icontains=q) | Q(phone1__icontains=q))

    paginator = Paginator(clients, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'pos/client_list.html', {'page_obj': page_obj, 'q': q})


@login_required
def client_create_view(request):
    if request.method == 'POST':
        form = PersonForm(request.POST, request.FILES)
        if form.is_valid():
            client = form.save(commit=False)
            client.kind = Person.KIND_CLIENT
            client.save()
            messages.success(request, f'Cliente "{client.name}" registrado.')
            return redirect('client_list')
    else:
        form = PersonForm(initial={'kind': Person.KIND_CLIENT})
    return render(request, 'pos/client_form.html', {'form': form, 'title': 'Nuevo cliente'})


@admin_required
def client_update_view(request, pk):
    client = get_object_or_404(Person, pk=pk, kind=Person.KIND_CLIENT)
    if request.method == 'POST':
        form = PersonForm(request.POST, request.FILES, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, f'Cliente "{client.name}" actualizado.')
            return redirect('client_list')
    else:
        form = PersonForm(instance=client)
    return render(request, 'pos/client_form.html', {'form': form, 'title': 'Editar cliente', 'client': client})


@admin_required
def client_delete_view(request, pk):
    client = get_object_or_404(Person, pk=pk, kind=Person.KIND_CLIENT)
    if request.method == 'POST':
        name = client.name
        client.delete()
        messages.success(request, f'Cliente "{name}" eliminado.')
        return redirect('client_list')
    return render(request, 'pos/confirm_delete.html', {'object': client, 'type': 'cliente', 'cancel_url': 'client_list'})


# ==========================================
# PROVEEDORES (Solo Admin)
# ==========================================
@admin_required
def provider_list_view(request):
    q = request.GET.get('q', '').strip()
    providers = Person.objects.filter(kind=Person.KIND_PROVIDER).order_by('-id')
    if q:
        providers = providers.filter(Q(name__icontains=q) | Q(company__icontains=q) | Q(phone1__icontains=q))

    paginator = Paginator(providers, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'pos/provider_list.html', {'page_obj': page_obj, 'q': q})


@admin_required
def provider_create_view(request):
    if request.method == 'POST':
        form = PersonForm(request.POST, request.FILES)
        if form.is_valid():
            provider = form.save(commit=False)
            provider.kind = Person.KIND_PROVIDER
            provider.save()
            messages.success(request, f'Proveedor "{provider.name}" registrado.')
            return redirect('provider_list')
    else:
        form = PersonForm(initial={'kind': Person.KIND_PROVIDER})
    return render(request, 'pos/provider_form.html', {'form': form, 'title': 'Nuevo proveedor'})


@admin_required
def provider_update_view(request, pk):
    provider = get_object_or_404(Person, pk=pk, kind=Person.KIND_PROVIDER)
    if request.method == 'POST':
        form = PersonForm(request.POST, request.FILES, instance=provider)
        if form.is_valid():
            form.save()
            messages.success(request, f'Proveedor "{provider.name}" actualizado.')
            return redirect('provider_list')
    else:
        form = PersonForm(instance=provider)
    return render(request, 'pos/provider_form.html', {'form': form, 'title': 'Editar proveedor', 'provider': provider})


@admin_required
def provider_delete_view(request, pk):
    provider = get_object_or_404(Person, pk=pk, kind=Person.KIND_PROVIDER)
    if request.method == 'POST':
        name = provider.name
        provider.delete()
        messages.success(request, f'Proveedor "{name}" eliminado.')
        return redirect('provider_list')
    return render(request, 'pos/confirm_delete.html', {'object': provider, 'type': 'proveedor', 'cancel_url': 'provider_list'})


# ==========================================
# MÓDULO DE USUARIOS (Solo Admin)
# ==========================================
@admin_required
def user_list_view(request):
    q = request.GET.get('q', '').strip()
    users = User.objects.all().select_related('profile').order_by('-date_joined')
    if q:
        users = users.filter(
            Q(username__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q)
        )

    paginator = Paginator(users, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'pos/user_list.html', {'page_obj': page_obj, 'q': q})


@admin_required
def user_create_view(request):
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Usuario "{user.username}" creado con éxito.')
            return redirect('user_list')
    else:
        form = UserCreateForm(initial={'kind': 2, 'is_active': True})
    return render(request, 'pos/user_form.html', {'form': form, 'title': 'Nuevo usuario'})


@admin_required
def user_update_view(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=user_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f'Usuario "{user_obj.username}" actualizado.')
            return redirect('user_list')
    else:
        form = UserUpdateForm(instance=user_obj)
    return render(request, 'pos/user_form.html', {'form': form, 'title': 'Editar usuario', 'edit_user': user_obj})


@admin_required
def user_delete_view(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if user_obj.id == request.user.id:
        messages.error(request, "No puedes eliminar tu propia cuenta de usuario en sesión.")
        return redirect('user_list')

    if request.method == 'POST':
        username = user_obj.username
        user_obj.delete()
        messages.success(request, f'Usuario "{username}" eliminado.')
        return redirect('user_list')
    return render(request, 'pos/confirm_delete.html', {'object': user_obj.username, 'type': 'usuario', 'cancel_url': 'user_list'})


def parse_date_range(request):
    """Auxiliar para procesar rango de fechas en reportes."""
    today = timezone.now().date()
    start_str = request.GET.get('start_date', '').strip()
    end_str = request.GET.get('end_date', '').strip()

    if start_str:
        try:
            start_date = datetime.date.fromisoformat(start_str)
        except ValueError:
            start_date = today.replace(day=1)
    else:
        start_date = today.replace(day=1)

    if end_str:
        try:
            end_date = datetime.date.fromisoformat(end_str)
        except ValueError:
            end_date = today
    else:
        end_date = today

    return start_date, end_date


# ==========================================
# TICKETS DE VENTA Y COMPRA
# ==========================================
@login_required
def ticket_sale_view(request, pk):
    sell = get_object_or_404(Sell.objects.select_related('person', 'user'), pk=pk, operation_type_id=2)
    config = get_config_dict()
    calculated_subtotal = sum(op.q * op.product.price_out for op in sell.operations.all())
    return render(request, 'pos/ticket_sale.html', {
        'sell': sell,
        'config': config,
        'calculated_subtotal': calculated_subtotal
    })


@login_required
def ticket_sale_pdf_view(request, pk):
    sell = get_object_or_404(Sell.objects.select_related('person', 'user'), pk=pk, operation_type_id=2)
    pdf_buffer = generate_sale_ticket_pdf(sell)
    return FileResponse(pdf_buffer, as_attachment=False, filename=f"ticket_venta_{sell.id}.pdf", content_type="application/pdf")


@admin_required
def ticket_purchase_view(request, pk):
    sell = get_object_or_404(Sell.objects.select_related('person', 'user'), pk=pk, operation_type_id=1)
    config = get_config_dict()
    return render(request, 'pos/ticket_purchase.html', {
        'sell': sell,
        'config': config
    })


@admin_required
def ticket_purchase_pdf_view(request, pk):
    sell = get_object_or_404(Sell.objects.select_related('person', 'user'), pk=pk, operation_type_id=1)
    pdf_buffer = generate_purchase_ticket_pdf(sell)
    return FileResponse(pdf_buffer, as_attachment=False, filename=f"ticket_compra_{sell.id}.pdf", content_type="application/pdf")


# ==========================================
# REPORTES (Ventas, Compras, Movimientos)
# ==========================================
@admin_required
def report_sales_view(request):
    start_date, end_date = parse_date_range(request)
    sales = Sell.objects.filter(
        operation_type_id=2,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).select_related('person', 'user').order_by('-created_at')

    total_count = sales.count()
    total_amount = sales.aggregate(total=Sum('total'))['total'] or 0.0
    average_amount = (total_amount / total_count) if total_count > 0 else 0.0

    context = {
        'sales': sales,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'total_count': total_count,
        'total_amount': total_amount,
        'average_amount': average_amount,
    }
    return render(request, 'pos/report_sales.html', context)


@admin_required
def report_sales_pdf_view(request):
    start_date, end_date = parse_date_range(request)
    sales = Sell.objects.filter(
        operation_type_id=2,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).select_related('person', 'user').order_by('-created_at')

    pdf_buffer = generate_sales_report_pdf(sales, start_date, end_date)
    return FileResponse(pdf_buffer, as_attachment=True, filename=f"reporte_ventas_{start_date}_{end_date}.pdf", content_type="application/pdf")


@admin_required
def report_purchases_view(request):
    start_date, end_date = parse_date_range(request)
    purchases = Sell.objects.filter(
        operation_type_id=1,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).select_related('person', 'user').order_by('-created_at')

    total_count = purchases.count()
    total_amount = purchases.aggregate(total=Sum('total'))['total'] or 0.0
    average_amount = (total_amount / total_count) if total_count > 0 else 0.0

    context = {
        'purchases': purchases,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'total_count': total_count,
        'total_amount': total_amount,
        'average_amount': average_amount,
    }
    return render(request, 'pos/report_purchases.html', context)


@admin_required
def report_purchases_pdf_view(request):
    start_date, end_date = parse_date_range(request)
    purchases = Sell.objects.filter(
        operation_type_id=1,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).select_related('person', 'user').order_by('-created_at')

    pdf_buffer = generate_purchases_report_pdf(purchases, start_date, end_date)
    return FileResponse(pdf_buffer, as_attachment=True, filename=f"reporte_compras_{start_date}_{end_date}.pdf", content_type="application/pdf")


@admin_required
def report_movements_view(request):
    start_date, end_date = parse_date_range(request)
    type_id = request.GET.get('type', '').strip()

    movements = Operation.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).select_related('product', 'operation_type', 'sell', 'sell__user').order_by('-created_at')

    if type_id in ['1', '2']:
        movements = movements.filter(operation_type_id=int(type_id))

    total_count = movements.count()
    total_in = movements.filter(operation_type_id=1).aggregate(t=Sum('q'))['t'] or 0.0
    total_out = movements.filter(operation_type_id=2).aggregate(t=Sum('q'))['t'] or 0.0

    context = {
        'movements': movements,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'selected_type': type_id,
        'total_count': total_count,
        'total_in': total_in,
        'total_out': total_out,
    }
    return render(request, 'pos/report_movements.html', context)


@admin_required
def report_movements_pdf_view(request):
    start_date, end_date = parse_date_range(request)
    type_id = request.GET.get('type', '').strip()

    movements = Operation.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).select_related('product', 'operation_type', 'sell', 'sell__user').order_by('-created_at')

    if type_id in ['1', '2']:
        movements = movements.filter(operation_type_id=int(type_id))

    pdf_buffer = generate_movements_report_pdf(movements, start_date, end_date)
    return FileResponse(pdf_buffer, as_attachment=True, filename=f"reporte_movimientos_{start_date}_{end_date}.pdf", content_type="application/pdf")


# ==========================================
# CONFIGURACIÓN (Tabla configuration)
# ==========================================
@admin_required
def configuration_view(request):
    if request.method == 'POST':
        fields = {
            'title': ('Titulo del Sistema', 2),
            'company_name': ('Nombre de la Empresa', 2),
            'company_phone': ('Teléfono de Contacto', 2),
            'company_address': ('Dirección del Negocio', 2),
            'ticket_footer': ('Mensaje al pie del ticket', 2),
        }
        for short_key, (name, kind) in fields.items():
            val = request.POST.get(short_key, '').strip()
            Configuration.objects.update_or_create(
                short=short_key,
                defaults={'name': name, 'kind': kind, 'val': val}
            )

        messages.success(request, "Configuración guardada correctamente.")
        return redirect('configuration_view')

    config = get_config_dict()
    return render(request, 'pos/configuration.html', {'config': config})
