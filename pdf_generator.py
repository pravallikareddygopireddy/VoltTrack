import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def generate_invoice_pdf(sale_data, items_data, warranties_data):
    """
    Generates a PDF invoice in memory using ReportLab.
    Returns bytes buffer.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#0B0F19')
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#475569')
    )
    inv_title_style = ParagraphStyle(
        'InvTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        alignment=2, # Right aligned
        textColor=colors.HexColor('#2563EB')
    )
    inv_meta_style = ParagraphStyle(
        'InvMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        alignment=2,
        textColor=colors.HexColor('#334155')
    )
    bold_label = ParagraphStyle(
        'BoldLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1E293B')
    )
    normal_text = ParagraphStyle(
        'NormalText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#334155')
    )

    story = []

    # Header Row (Company Info on Left, Invoice # on Right)
    header_left = [
        Paragraph("⚡ <b>VoltTrack Battery Hub</b>", title_style),
        Paragraph("Authorized Dealer: Exide | Amaron | Luminous | SF Sonic", subtitle_style),
        Paragraph("101 Power House Road, Auto Nagar, Hyderabad - 500032", subtitle_style),
        Paragraph("GSTIN: 36ABCDE1234F1Z5 | Ph: +91 98765 00000", subtitle_style)
    ]

    header_right = [
        Paragraph("TAX INVOICE", inv_title_style),
        Paragraph(f"<b>Invoice #:</b> {sale_data['invoice_no']}", inv_meta_style),
        Paragraph(f"<b>Date:</b> {sale_data['sale_date']}", inv_meta_style),
        Paragraph(f"<b>Payment Mode:</b> {sale_data['payment_mode']}", inv_meta_style)
    ]

    header_table = Table([[header_left, header_right]], colWidths=[340, 200])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563EB'), spaceAfter=15))

    # Customer Details Row
    cust_info = [
        [Paragraph("<b>CUSTOMER DETAILS</b>", bold_label)],
        [Paragraph(f"<b>Name:</b> {sale_data['customer_name']}", normal_text)],
        [Paragraph(f"<b>Phone:</b> {sale_data['customer_phone']}", normal_text)],
        [Paragraph(f"<b>Address:</b> {sale_data.get('customer_address', 'N/A')}", normal_text)],
    ]
    cust_table = Table(cust_info, colWidths=[540])
    cust_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
    ]))
    story.append(cust_table)
    story.append(Spacer(1, 15))

    # Items Table
    table_data = [
        [
            Paragraph("<b>#</b>", bold_label),
            Paragraph("<b>Item Description</b>", bold_label),
            Paragraph("<b>Brand</b>", bold_label),
            Paragraph("<b>Qty</b>", bold_label),
            Paragraph("<b>Price (₹)</b>", bold_label),
            Paragraph("<b>Total (₹)</b>", bold_label)
        ]
    ]

    for idx, item in enumerate(items_data, start=1):
        table_data.append([
            Paragraph(str(idx), normal_text),
            Paragraph(item['product_name'], normal_text),
            Paragraph(item['brand'], normal_text),
            Paragraph(str(item['quantity']), normal_text),
            Paragraph(f"₹{item['unit_price']:,.2f}", normal_text),
            Paragraph(f"₹{item['total_price']:,.2f}", normal_text)
        ])

    items_table = Table(table_data, colWidths=[30, 230, 80, 40, 80, 80])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (3,0), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
    ]))

    # Override text color for table header
    header_cell_style = ParagraphStyle('HeaderCell', parent=bold_label, textColor=colors.white)
    table_data[0] = [
        Paragraph("<b>#</b>", header_cell_style),
        Paragraph("<b>Item Description</b>", header_cell_style),
        Paragraph("<b>Brand</b>", header_cell_style),
        Paragraph("<b>Qty</b>", header_cell_style),
        Paragraph("<b>Price (₹)</b>", header_cell_style),
        Paragraph("<b>Total (₹)</b>", header_cell_style)
    ]
    items_table = Table(table_data, colWidths=[30, 230, 80, 40, 80, 80])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
        ('ALIGN', (3,0), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))

    story.append(items_table)
    story.append(Spacer(1, 15))

    # Summary Totals (Right Aligned)
    subtotal = sale_data['subtotal']
    gst_rate = sale_data['gst_rate']
    gst_amount = sale_data['gst_amount']
    rebate = sale_data.get('old_battery_rebate', 0.0)
    grand_total = sale_data['total_amount']

    totals_data = [
        [Paragraph("Subtotal:", bold_label), Paragraph(f"₹{subtotal:,.2f}", normal_text)],
        [Paragraph(f"GST ({gst_rate:.1f}%):", bold_label), Paragraph(f"₹{gst_amount:,.2f}", normal_text)],
    ]
    if rebate > 0:
        totals_data.append([Paragraph("Old Battery Rebate (-):", bold_label), Paragraph(f"- ₹{rebate:,.2f}", normal_text)])

    totals_data.append([
        Paragraph("<b>GRAND TOTAL:</b>", ParagraphStyle('GrandLbl', parent=bold_label, fontSize=12, textColor=colors.HexColor('#2563EB'))),
        Paragraph(f"<b>₹{grand_total:,.2f}</b>", ParagraphStyle('GrandVal', parent=bold_label, fontSize=12, textColor=colors.HexColor('#2563EB')))
    ])

    totals_table = Table(totals_data, colWidths=[140, 100])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('PADDING', (0,0), (-1,-1), 4),
        ('LINEABOVE', (0,-1), (-1,-1), 1, colors.HexColor('#2563EB')),
    ]))

    summary_wrapper = Table([[Paragraph("", normal_text), totals_table]], colWidths=[300, 240])
    summary_wrapper.setStyle(TableStyle([
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(summary_wrapper)
    story.append(Spacer(1, 15))

    # Warranty Details Section
    if warranties_data:
        story.append(Paragraph("<b>REGISTERED WARRANTY DETAILS</b>", bold_label))
        story.append(Spacer(1, 4))
        w_data = [
            [
                Paragraph("<b>Product</b>", header_cell_style),
                Paragraph("<b>Serial Number</b>", header_cell_style),
                Paragraph("<b>Warranty</b>", header_cell_style),
                Paragraph("<b>Expires On</b>", header_cell_style)
            ]
        ]
        for w in warranties_data:
            w_data.append([
                Paragraph(w['product_name'], normal_text),
                Paragraph(f"<b>{w['serial_number']}</b>", normal_text),
                Paragraph(f"{w['warranty_months']} Months", normal_text),
                Paragraph(w['expiry_date'], normal_text)
            ])
        w_table = Table(w_data, colWidths=[200, 160, 90, 90])
        w_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(w_table)
        story.append(Spacer(1, 15))

    # Terms & Signature
    terms_text = "<b>Terms & Conditions:</b><br/>1. Goods once sold will not be taken back without valid reason.<br/>2. Manufacturer warranty terms apply. Preserve this bill & serial number for warranty claims.<br/>3. Subject to local jurisdiction."
    story.append(Paragraph(terms_text, subtitle_style))
    story.append(Spacer(1, 25))

    sign_data = [
        [Paragraph("Customer Signature", subtitle_style), Paragraph("For VoltTrack Battery Hub<br/><br/><b>Authorized Signatory</b>", ParagraphStyle('SignRight', parent=subtitle_style, alignment=2))]
    ]
    sign_table = Table(sign_data, colWidths=[270, 270])
    sign_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM')
    ]))
    story.append(sign_table)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
