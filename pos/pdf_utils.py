import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, inch

from .models import Configuration


def get_config_dict():
    """Retorna un diccionario con las configuraciones del sistema."""
    configs = Configuration.objects.all()
    data = {c.short: c.val for c in configs}
    defaults = {
        'title': 'DizzyPOS',
        'company_name': 'DizzyPOS - Tienda & Ventas',
        'company_phone': '555-000-0000',
        'company_address': 'Av. Principal #100',
        'ticket_footer': '¡Gracias por su compra!',
    }
    for k, v in defaults.items():
        if k not in data or not data[k]:
            data[k] = v
    return data


# ==========================================
# GENERADORES DE TICKETS EN PDF
# ==========================================

def generate_sale_ticket_pdf(sell):
    """Genera el PDF del ticket de venta en formato recibo (80mm de ancho)."""
    buffer = io.BytesIO()
    configs = get_config_dict()
    ticket_width = 72 * mm
    ticket_height = 220 * mm

    doc = SimpleDocTemplate(
        buffer,
        pagesize=(ticket_width, ticket_height),
        leftMargin=3 * mm,
        rightMargin=3 * mm,
        topMargin=5 * mm,
        bottomMargin=5 * mm
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TicketTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=14,
        alignment=1
    )
    center_small = ParagraphStyle(
        'CenterSmall',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9,
        alignment=1,
        textColor=colors.HexColor('#444444')
    )
    normal_style = ParagraphStyle(
        'TicketNormal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10
    )
    bold_style = ParagraphStyle(
        'TicketBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10
    )

    elements = []

    # Encabezado
    elements.append(Paragraph(configs['company_name'], title_style))
    elements.append(Paragraph(configs['company_address'], center_small))
    elements.append(Paragraph(f"Tel: {configs['company_phone']}", center_small))
    elements.append(Spacer(1, 2 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.8, color=colors.black, spaceAfter=2 * mm))

    # Datos de la venta
    elements.append(Paragraph(f"<b>TICKET DE VENTA: #{sell.id}</b>", bold_style))
    elements.append(Paragraph(f"Fecha: {sell.created_at.strftime('%d/%m/%Y %H:%M')}", normal_style))
    elements.append(Paragraph(f"Cajero: {sell.user.first_name or sell.user.username if sell.user else 'General'}", normal_style))
    client_name = sell.person.full_name if sell.person else 'Público en general'
    elements.append(Paragraph(f"Cliente: {client_name}", normal_style))
    elements.append(Spacer(1, 2 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey, spaceAfter=2 * mm))

    # Detalle de artículos
    table_data = [
        [
            Paragraph("<b>Cant</b>", normal_style),
            Paragraph("<b>Producto</b>", normal_style),
            Paragraph("<b>Precio</b>", normal_style),
            Paragraph("<b>Total</b>", normal_style)
        ]
    ]

    for op in sell.operations.all():
        subtotal = op.q * op.product.price_out
        table_data.append([
            Paragraph(f"{op.q:.0f}", normal_style),
            Paragraph(op.product.name[:18], normal_style),
            Paragraph(f"${op.product.price_out:.2f}", normal_style),
            Paragraph(f"${subtotal:.2f}", normal_style)
        ])

    items_table = Table(table_data, colWidths=[10 * mm, 28 * mm, 14 * mm, 14 * mm])
    items_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 2 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey, spaceAfter=2 * mm))

    # Totales
    totals_data = []
    if sell.discount and sell.discount > 0:
        totals_data.append([Paragraph("Subtotal:", normal_style), Paragraph(f"${sell.total + sell.discount:.2f}", normal_style)])
        totals_data.append([Paragraph("Descuento:", normal_style), Paragraph(f"-${sell.discount:.2f}", normal_style)])

    totals_data.append([Paragraph("<b>TOTAL:</b>", bold_style), Paragraph(f"<b>${sell.total:.2f}</b>", bold_style)])
    totals_data.append([Paragraph("Pago recibido:", normal_style), Paragraph(f"${sell.cash:.2f}", normal_style)])
    totals_data.append([Paragraph("<b>Cambio:</b>", bold_style), Paragraph(f"<b>${sell.change:.2f}</b>", bold_style)])

    totals_table = Table(totals_data, colWidths=[36 * mm, 30 * mm])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
    ]))
    elements.append(totals_table)

    # Frase de agradecimiento
    elements.append(Spacer(1, 4 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.8, color=colors.black, spaceAfter=2 * mm))
    elements.append(Paragraph(configs['ticket_footer'], center_small))

    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_purchase_ticket_pdf(sell):
    """Genera el PDF del ticket de compra en formato recibo (80mm de ancho)."""
    buffer = io.BytesIO()
    configs = get_config_dict()
    ticket_width = 72 * mm
    ticket_height = 220 * mm

    doc = SimpleDocTemplate(
        buffer,
        pagesize=(ticket_width, ticket_height),
        leftMargin=3 * mm,
        rightMargin=3 * mm,
        topMargin=5 * mm,
        bottomMargin=5 * mm
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TicketTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=14,
        alignment=1
    )
    center_small = ParagraphStyle(
        'CenterSmall',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9,
        alignment=1,
        textColor=colors.HexColor('#444444')
    )
    normal_style = ParagraphStyle(
        'TicketNormal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10
    )
    bold_style = ParagraphStyle(
        'TicketBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10
    )

    elements = []

    # Encabezado
    elements.append(Paragraph(configs['company_name'], title_style))
    elements.append(Paragraph(configs['company_address'], center_small))
    elements.append(Paragraph(f"Tel: {configs['company_phone']}", center_small))
    elements.append(Spacer(1, 2 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.8, color=colors.black, spaceAfter=2 * mm))

    # Datos de la compra
    elements.append(Paragraph(f"<b>COMPROBANTE DE COMPRA: #{sell.id}</b>", bold_style))
    elements.append(Paragraph(f"Fecha: {sell.created_at.strftime('%d/%m/%Y %H:%M')}", normal_style))
    elements.append(Paragraph(f"Registrado por: {sell.user.first_name or sell.user.username if sell.user else 'General'}", normal_style))
    prov_name = sell.person.full_name if sell.person else 'Proveedor general'
    if sell.person and sell.person.company:
        prov_name += f" ({sell.person.company})"
    elements.append(Paragraph(f"Proveedor: {prov_name}", normal_style))
    elements.append(Spacer(1, 2 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey, spaceAfter=2 * mm))

    # Detalle de artículos
    table_data = [
        [
            Paragraph("<b>Cant</b>", normal_style),
            Paragraph("<b>Producto</b>", normal_style),
            Paragraph("<b>Costo</b>", normal_style),
            Paragraph("<b>Total</b>", normal_style)
        ]
    ]

    for op in sell.operations.all():
        subtotal = op.q * op.product.price_in
        table_data.append([
            Paragraph(f"{op.q:.0f}", normal_style),
            Paragraph(op.product.name[:18], normal_style),
            Paragraph(f"${op.product.price_in:.2f}", normal_style),
            Paragraph(f"${subtotal:.2f}", normal_style)
        ])

    items_table = Table(table_data, colWidths=[10 * mm, 28 * mm, 14 * mm, 14 * mm])
    items_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 2 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey, spaceAfter=2 * mm))

    # Total
    totals_data = [
        [Paragraph("<b>TOTAL COMPRA:</b>", bold_style), Paragraph(f"<b>${sell.total:.2f}</b>", bold_style)]
    ]
    totals_table = Table(totals_data, colWidths=[36 * mm, 30 * mm])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
    ]))
    elements.append(totals_table)

    # Frase al pie
    elements.append(Spacer(1, 4 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.8, color=colors.black, spaceAfter=2 * mm))
    elements.append(Paragraph("Entrada al inventario registrada correctamente.", center_small))
    elements.append(Paragraph("¡Gracias por su compra!", center_small))

    doc.build(elements)
    buffer.seek(0)
    return buffer


# ==========================================
# GENERADORES DE REPORTES EN PDF (CARTA)
# ==========================================

def generate_sales_report_pdf(sales, start_date, end_date):
    """Genera reporte de ventas en PDF en tamaño carta."""
    buffer = io.BytesIO()
    configs = get_config_dict()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'RepTitle',
        parent=styles['Title'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        alignment=0,
        textColor=colors.HexColor('#0d6efd')
    )
    subtitle_style = ParagraphStyle(
        'RepSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#555555')
    )
    cell_style = ParagraphStyle('Cell', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=11)
    cell_bold = ParagraphStyle('CellB', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, leading=11)

    elements = []

    # Encabezado
    elements.append(Paragraph(configs['company_name'], subtitle_style))
    elements.append(Paragraph("Reporte de Ventas", title_style))
    elements.append(Paragraph(f"Período: <b>{start_date.strftime('%d/%m/%Y')}</b> al <b>{end_date.strftime('%d/%m/%Y')}</b> | Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", subtitle_style))
    elements.append(Spacer(1, 5 * mm))

    # Tabla
    table_data = [
        [
            Paragraph("<b>Folio</b>", cell_bold),
            Paragraph("<b>Fecha y hora</b>", cell_bold),
            Paragraph("<b>Cliente</b>", cell_bold),
            Paragraph("<b>Atendido por</b>", cell_bold),
            Paragraph("<b>Descuento</b>", cell_bold),
            Paragraph("<b>Total</b>", cell_bold)
        ]
    ]

    total_amount = 0.0
    for s in sales:
        total_amount += s.total or 0.0
        client = s.person.full_name if s.person else 'Público general'
        cashier = s.user.first_name or s.user.username if s.user else '-'
        disc_str = f"${s.discount:.2f}" if s.discount else "$0.00"
        table_data.append([
            Paragraph(f"#{s.id}", cell_style),
            Paragraph(s.created_at.strftime('%d/%m/%Y %H:%M'), cell_style),
            Paragraph(client[:24], cell_style),
            Paragraph(cashier[:18], cell_style),
            Paragraph(disc_str, cell_style),
            Paragraph(f"${s.total:.2f}", cell_bold)
        ])

    table = Table(table_data, colWidths=[20 * mm, 38 * mm, 50 * mm, 35 * mm, 25 * mm, 27 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ALIGN', (4, 1), (-1, -1), 'RIGHT'),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 6 * mm))

    # Resumen
    summary_data = [
        [Paragraph(f"<b>Total de ventas registradas:</b> {len(sales)}", subtitle_style),
         Paragraph(f"<b>Monto Total Facturado:</b> ${total_amount:,.2f}", cell_bold)]
    ]
    summary_table = Table(summary_data, colWidths=[100 * mm, 95 * mm])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
    ]))
    elements.append(summary_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_purchases_report_pdf(purchases, start_date, end_date):
    """Genera reporte de compras en PDF en tamaño carta."""
    buffer = io.BytesIO()
    configs = get_config_dict()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'RepTitle',
        parent=styles['Title'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        alignment=0,
        textColor=colors.HexColor('#198754')
    )
    subtitle_style = ParagraphStyle(
        'RepSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#555555')
    )
    cell_style = ParagraphStyle('Cell', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=11)
    cell_bold = ParagraphStyle('CellB', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, leading=11)

    elements = []

    # Encabezado
    elements.append(Paragraph(configs['company_name'], subtitle_style))
    elements.append(Paragraph("Reporte de Compras", title_style))
    elements.append(Paragraph(f"Período: <b>{start_date.strftime('%d/%m/%Y')}</b> al <b>{end_date.strftime('%d/%m/%Y')}</b> | Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", subtitle_style))
    elements.append(Spacer(1, 5 * mm))

    # Tabla
    table_data = [
        [
            Paragraph("<b>Folio</b>", cell_bold),
            Paragraph("<b>Fecha y hora</b>", cell_bold),
            Paragraph("<b>Proveedor</b>", cell_bold),
            Paragraph("<b>Empresa</b>", cell_bold),
            Paragraph("<b>Registrado por</b>", cell_bold),
            Paragraph("<b>Total Compra</b>", cell_bold)
        ]
    ]

    total_amount = 0.0
    for p in purchases:
        total_amount += p.total or 0.0
        prov = p.person.full_name if p.person else 'Proveedor general'
        comp = p.person.company if p.person and p.person.company else '-'
        user_name = p.user.first_name or p.user.username if p.user else '-'
        table_data.append([
            Paragraph(f"#{p.id}", cell_style),
            Paragraph(p.created_at.strftime('%d/%m/%Y %H:%M'), cell_style),
            Paragraph(prov[:22], cell_style),
            Paragraph(comp[:22], cell_style),
            Paragraph(user_name[:18], cell_style),
            Paragraph(f"${p.total:.2f}", cell_bold)
        ])

    table = Table(table_data, colWidths=[20 * mm, 38 * mm, 45 * mm, 40 * mm, 25 * mm, 27 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ALIGN', (5, 1), (-1, -1), 'RIGHT'),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 6 * mm))

    # Resumen
    summary_data = [
        [Paragraph(f"<b>Total de compras registradas:</b> {len(purchases)}", subtitle_style),
         Paragraph(f"<b>Monto Total Comprado:</b> ${total_amount:,.2f}", cell_bold)]
    ]
    summary_table = Table(summary_data, colWidths=[100 * mm, 95 * mm])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
    ]))
    elements.append(summary_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_movements_report_pdf(movements, start_date, end_date):
    """Genera reporte de movimientos de inventario en PDF en tamaño carta."""
    buffer = io.BytesIO()
    configs = get_config_dict()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'RepTitle',
        parent=styles['Title'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        alignment=0,
        textColor=colors.HexColor('#0f172a')
    )
    subtitle_style = ParagraphStyle(
        'RepSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#555555')
    )
    cell_style = ParagraphStyle('Cell', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, leading=10.5)
    cell_bold = ParagraphStyle('CellB', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, leading=10.5)

    elements = []

    # Encabezado
    elements.append(Paragraph(configs['company_name'], subtitle_style))
    elements.append(Paragraph("Reporte de Movimientos de Inventario", title_style))
    elements.append(Paragraph(f"Período: <b>{start_date.strftime('%d/%m/%Y')}</b> al <b>{end_date.strftime('%d/%m/%Y')}</b> | Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", subtitle_style))
    elements.append(Spacer(1, 5 * mm))

    # Tabla
    table_data = [
        [
            Paragraph("<b>Fecha y hora</b>", cell_bold),
            Paragraph("<b>Tipo</b>", cell_bold),
            Paragraph("<b>Producto</b>", cell_bold),
            Paragraph("<b>Código</b>", cell_bold),
            Paragraph("<b>Cant.</b>", cell_bold),
            Paragraph("<b>Referencia</b>", cell_bold),
            Paragraph("<b>Usuario</b>", cell_bold)
        ]
    ]

    total_in = 0.0
    total_out = 0.0

    for op in movements:
        is_in = (op.operation_type_id == 1)
        if is_in:
            total_in += op.q
            tipo_txt = '<font color="#198754"><b>ENTRADA</b></font>'
            ref_txt = f"Compra #{op.sell_id}" if op.sell_id else "Ajuste"
        else:
            total_out += op.q
            tipo_txt = '<font color="#dc3545"><b>SALIDA</b></font>'
            ref_txt = f"Venta #{op.sell_id}" if op.sell_id else "Ajuste"

        user_name = op.sell.user.username if op.sell and op.sell.user else '-'
        table_data.append([
            Paragraph(op.created_at.strftime('%d/%m/%Y %H:%M'), cell_style),
            Paragraph(tipo_txt, cell_style),
            Paragraph(op.product.name[:25], cell_style),
            Paragraph(op.product.barcode or '-', cell_style),
            Paragraph(f"{op.q:.0f}", cell_bold),
            Paragraph(ref_txt, cell_style),
            Paragraph(user_name[:15], cell_style)
        ])

    table = Table(table_data, colWidths=[33 * mm, 22 * mm, 52 * mm, 25 * mm, 15 * mm, 25 * mm, 23 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ALIGN', (4, 1), (4, -1), 'CENTER'),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 6 * mm))

    # Resumen
    summary_data = [
        [
            Paragraph(f"<b>Total movimientos:</b> {len(movements)}", subtitle_style),
            Paragraph(f"<b>Unidades Entradas (+):</b> {total_in:.0f}", subtitle_style),
            Paragraph(f"<b>Unidades Salidas (-):</b> {total_out:.0f}", subtitle_style)
        ]
    ]
    summary_table = Table(summary_data, colWidths=[65 * mm, 65 * mm, 65 * mm])
    summary_table.setStyle(TableStyle([
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
    ]))
    elements.append(summary_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer
