import os
import sqlite3
import uuid
import random

from flask import render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
import io
from datetime import datetime, timedelta
import database
from pdf_generator import generate_invoice_pdf

app = Flask(__name__)
app.secret_key = 'volttrack_secret_key_battery_shop_2026'
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def init_shop_settings_table():
    conn = database.get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS shop_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            shop_name TEXT NOT NULL DEFAULT '',
            owner_name TEXT DEFAULT '',
            address TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            gstin TEXT DEFAULT '',
            logo_path TEXT DEFAULT ''
        )
    """)

    conn.execute("""
        INSERT OR IGNORE INTO shop_settings (id, shop_name)
        VALUES (1, '')
    """)

    conn.commit()
    conn.close()


def get_shop_settings():
    conn = database.get_db()
    shop = conn.execute(
        "SELECT * FROM shop_settings WHERE id = 1"
    ).fetchone()
    conn.close()
    return shop

@app.context_processor
def inject_shop_details():
    return {"shop": get_shop_settings()}


def allowed_shop_logo(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_LOGO_EXTENSIONS
    )


init_shop_settings_table()


@app.context_processor
def inject_shop_details():
    return {"shop": get_shop_settings()}


SHOP_LOGO_FOLDER = os.path.join(
    BASE_DIR, "static", "uploads", "shop"
)

ALLOWED_LOGO_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

os.makedirs(SHOP_LOGO_FOLDER, exist_ok=True)

# Ensure DB is initialized
database.init_db()

@app.route('/')
def dashboard():
    conn = database.get_db()
    cursor = conn.cursor()

    # 1. Total Products (SKUs)
    cursor.execute('SELECT COUNT(*) FROM products')
    total_products = cursor.fetchone()[0]

    # 2. Total Batteries in Stock
    cursor.execute('SELECT COALESCE(SUM(stock_qty), 0) FROM products')
    total_batteries = cursor.fetchone()[0]

    # 3. Low Stock Items Count
    cursor.execute('SELECT COUNT(*) FROM products WHERE stock_qty <= min_stock_alert')
    low_stock_count = cursor.fetchone()[0]

    # 4. Today's Sales
    today_str = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("SELECT COALESCE(SUM(total_amount), 0) FROM sales WHERE DATE(sale_date) = ?", (today_str,))
    today_sales = cursor.fetchone()[0]

    # 5. Category Breakdown (Count of Batteries in stock per category)
    cursor.execute('''
        SELECT category, COALESCE(SUM(stock_qty), 0) as total_qty, COUNT(id) as product_count
        FROM products
        GROUP BY category
    ''')
    category_rows = cursor.fetchall()
    
    # Standard categories dictionary mapping
    category_counts = {
        'Vehicle Batteries': 0,
        'Two-wheeler Batteries': 0,
        'Inverter Batteries': 0,
        'Other Battery types': 0
    }
    for row in category_rows:
        category_counts[row['category']] = row['total_qty']

    # 6. Recent Sales (Last 5)
    cursor.execute('''
        SELECT s.*, (SELECT COUNT(*) FROM sale_items WHERE sale_id = s.id) as item_count
        FROM sales s
        ORDER BY s.sale_date DESC LIMIT 5
    ''')
    recent_sales = cursor.fetchall()

    # 7. Low Stock Products list
    cursor.execute('''
        SELECT * FROM products
        WHERE stock_qty <= min_stock_alert
        ORDER BY stock_qty ASC LIMIT 6
    ''')
    low_stock_products = cursor.fetchall()

    # 8. Brand distribution for charts
    cursor.execute('''
        SELECT brand, SUM(stock_qty) as total_qty
        FROM products
        GROUP BY brand
    ''')
    brand_data = cursor.fetchall()

    conn.close()

    return render_template(
        'dashboard.html',
        total_products=total_products,
        total_batteries=total_batteries,
        low_stock_count=low_stock_count,
        today_sales=today_sales,
        category_counts=category_counts,
        recent_sales=recent_sales,
        low_stock_products=low_stock_products,
        brand_data=brand_data
    )

@app.route('/products')
def products():
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    brand = request.args.get('brand', '').strip()
    low_stock = request.args.get('low_stock', '').strip()

    conn = database.get_db()
    cursor = conn.cursor()

    query = 'SELECT * FROM products WHERE 1=1'
    params = []

    if search:
        query += ' AND (name LIKE ? OR model LIKE ? OR brand LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])
    if category:
        query += ' AND category = ?'
        params.append(category)
    if brand:
        query += ' AND brand = ?'
        params.append(brand)
    if low_stock == '1':
        query += ' AND stock_qty <= min_stock_alert'

    query += ' ORDER BY id DESC'
    cursor.execute(query, params)
    products_list = cursor.fetchall()

    # Get distinct brands & categories for dropdown filters
    cursor.execute('SELECT DISTINCT brand FROM products ORDER BY brand')
    brands = [r['brand'] for r in cursor.fetchall()]

    cursor.execute('SELECT DISTINCT name FROM suppliers ORDER BY name')
    suppliers = [r['name'] for r in cursor.fetchall()]

    conn.close()

    return render_template(
        'products.html',
        products=products_list,
        brands=brands,
        suppliers=suppliers,
        search=search,
        selected_category=category,
        selected_brand=brand,
        low_stock_filter=low_stock
    )

@app.route('/products/add', methods=['POST'])
def add_product():
    try:
        name = request.form['name']
        brand = request.form['brand']
        model = request.form['model']
        category = request.form['category']
        capacity = request.form['capacity']
        voltage = request.form.get('voltage', '12V')
        warranty_months = int(request.form.get('warranty_months', 24))
        purchase_price = float(request.form['purchase_price'])
        selling_price = float(request.form['selling_price'])
        stock_qty = int(request.form['stock_qty'])
        min_stock_alert = int(request.form.get('min_stock_alert', 5))
        supplier_name = request.form.get('supplier_name', '')
        supplier_phone = request.form.get('supplier_phone', '')

        conn = database.get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO products (name, brand, model, category, capacity, voltage, warranty_months, purchase_price, selling_price, stock_qty, min_stock_alert, supplier_name, supplier_phone)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, brand, model, category, capacity, voltage, warranty_months, purchase_price, selling_price, stock_qty, min_stock_alert, supplier_name, supplier_phone))
        conn.commit()
        conn.close()

        flash(f'Battery product "{name}" added successfully!', 'success')
    except Exception as e:
        flash(f'Error adding product: {str(e)}', 'danger')

    return redirect(url_for('products'))

@app.route('/products/edit/<int:product_id>', methods=['POST'])
def edit_product(product_id):
    try:
        name = request.form['name']
        brand = request.form['brand']
        model = request.form['model']
        category = request.form['category']
        capacity = request.form['capacity']
        voltage = request.form.get('voltage', '12V')
        warranty_months = int(request.form.get('warranty_months', 24))
        purchase_price = float(request.form['purchase_price'])
        selling_price = float(request.form['selling_price'])
        stock_qty = int(request.form['stock_qty'])
        min_stock_alert = int(request.form.get('min_stock_alert', 5))
        supplier_name = request.form.get('supplier_name', '')
        supplier_phone = request.form.get('supplier_phone', '')

        conn = database.get_db()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE products
            SET name=?, brand=?, model=?, category=?, capacity=?, voltage=?, warranty_months=?, purchase_price=?, selling_price=?, stock_qty=?, min_stock_alert=?, supplier_name=?, supplier_phone=?
            WHERE id=?
        ''', (name, brand, model, category, capacity, voltage, warranty_months, purchase_price, selling_price, stock_qty, min_stock_alert, supplier_name, supplier_phone, product_id))
        conn.commit()
        conn.close()

        flash(f'Product "{name}" updated successfully!', 'success')
    except Exception as e:
        flash(f'Error updating product: {str(e)}', 'danger')

    return redirect(url_for('products'))

@app.route('/products/update_stock/<int:product_id>', methods=['POST'])
def update_stock(product_id):
    change = int(request.form.get('change', 0))
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE products SET stock_qty = MAX(0, stock_qty + ?) WHERE id = ?', (change, product_id))
    conn.commit()
    conn.close()
    flash('Stock quantity updated successfully!', 'info')
    return redirect(url_for('products'))

@app.route('/products/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()
    flash('Product removed from inventory.', 'warning')
    return redirect(url_for('products'))

@app.route('/billing/create', methods=['GET', 'POST'])
def create_bill():
    conn = database.get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        try:
            customer_name = request.form['customer_name'].strip()
            customer_phone = request.form['customer_phone'].strip()
            customer_address = request.form.get('customer_address', '').strip()
            payment_mode = request.form.get('payment_mode', 'Cash')
            gst_rate = float(request.form.get('gst_rate', 18.0))
            old_battery_rebate = float(request.form.get('old_battery_rebate', 0.0))

            product_ids = request.form.getlist('product_id[]')
            quantities = request.form.getlist('quantity[]')
            prices = request.form.getlist('price[]')

            if not product_ids:
                flash('Please select at least one battery product to sell.', 'danger')
                return redirect(url_for('create_bill'))

            # Generate Invoice Number e.g. INV-2026-0004
            today_year = datetime.now().year
            cursor.execute('SELECT COUNT(*) FROM sales')
            sale_count = cursor.fetchone()[0] + 1
            invoice_no = f"INV-{today_year}-{sale_count:04d}"

            # Calculate item totals & subtotal
            subtotal = 0.0
            items_to_insert = []
            serials_to_register = []

            for i in range(len(product_ids)):
                p_id = int(product_ids[i])
                qty = int(quantities[i])
                price = float(prices[i])
                total_item_price = price * qty

                # Get product details
                cursor.execute('SELECT * FROM products WHERE id = ?', (p_id,))
                prod = cursor.fetchone()

                if not prod or prod['stock_qty'] < qty:
                    flash(f"Insufficient stock for product '{prod['name'] if prod else 'Unknown'}'. Available: {prod['stock_qty'] if prod else 0}", 'danger')
                    conn.close()
                    return redirect(url_for('create_bill'))

                subtotal += total_item_price
                items_to_insert.append({
                    'product_id': p_id,
                    'product_name': prod['name'],
                    'brand': prod['brand'],
                    'quantity': qty,
                    'unit_price': price,
                    'total_price': total_item_price,
                    'warranty_months': prod['warranty_months']
                })

                # Retrieve serial numbers entered for this item
                serial_inputs = request.form.getlist(f'serials_{i}[]')
                for s_idx in range(qty):
                    sn = serial_inputs[s_idx].strip() if s_idx < len(serial_inputs) else ""
                    if not sn:
                        # Auto generate serial number if left empty
                        sn = f"{prod['brand'][:3].upper()}-{today_year}-{random.randint(10000, 99999)}"
                    
                    serials_to_register.append({
                        'product_id': p_id,
                        'product_name': prod['name'],
                        'serial_number': sn,
                        'warranty_months': prod['warranty_months']
                    })

            gst_amount = subtotal * (gst_rate / 100.0)
            total_amount = max(0.0, (subtotal + gst_amount) - old_battery_rebate)
            sale_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Insert Sale
            cursor.execute('''
                INSERT INTO sales (invoice_no, customer_name, customer_phone, customer_address, sale_date, subtotal, gst_rate, gst_amount, old_battery_rebate, total_amount, payment_mode)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (invoice_no, customer_name, customer_phone, customer_address, sale_date, subtotal, gst_rate, gst_amount, old_battery_rebate, total_amount, payment_mode))
            
            sale_id = cursor.lastrowid

            # Insert Sale Items & decrease stock
            for item in items_to_insert:
                cursor.execute('''
                    INSERT INTO sale_items (sale_id, product_id, product_name, brand, quantity, unit_price, total_price)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (sale_id, item['product_id'], item['product_name'], item['brand'], item['quantity'], item['unit_price'], item['total_price']))

                # Auto-decrease stock
                cursor.execute('UPDATE products SET stock_qty = stock_qty - ? WHERE id = ?', (item['quantity'], item['product_id']))

            # Insert Warranty Records
            today_dt = datetime.now()
            purch_date = today_dt.strftime('%Y-%m-%d')

            for s_item in serials_to_register:
                w_months = s_item['warranty_months']
                exp_date = (today_dt + timedelta(days=w_months*30)).strftime('%Y-%m-%d')

                cursor.execute('''
                    INSERT INTO warranties (sale_id, product_id, product_name, customer_name, customer_phone, serial_number, purchase_date, warranty_months, expiry_date, status, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active', 'Registered at sale')
                ''', (sale_id, s_item['product_id'], s_item['product_name'], customer_name, customer_phone, s_item['serial_number'], purch_date, w_months, exp_date))

            conn.commit()
            conn.close()

            flash(f'Invoice {invoice_no} created successfully! Warranty registered.', 'success')
            return redirect(url_for('view_invoice', sale_id=sale_id))

        except Exception as e:
            flash(f'Error generating invoice: {str(e)}', 'danger')
            conn.close()
            return redirect(url_for('create_bill'))

    # GET request: Load product list for selection dropdown
    cursor.execute('SELECT * FROM products WHERE stock_qty > 0 ORDER BY brand, name')
    products = cursor.fetchall()
    conn.close()

    return render_template('create_bill.html', products=products)
def get_shop_db_connection():
    conn = database.get_db()
    conn.row_factory = sqlite3.Row
    return conn


def init_shop_settings_table():
    conn = get_shop_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS shop_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            shop_name TEXT NOT NULL DEFAULT '',
            owner_name TEXT DEFAULT '',
            address TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            gstin TEXT DEFAULT '',
            logo_path TEXT DEFAULT ''
        )
    """)

    conn.execute("""
        INSERT OR IGNORE INTO shop_settings (id)
        VALUES (1)
    """)

    conn.commit()
    conn.close()


def get_shop_settings():
    conn = get_shop_db_connection()
    shop = conn.execute(
        "SELECT * FROM shop_settings WHERE id = 1"
    ).fetchone()
    conn.close()
    return shop


def allowed_shop_logo(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_LOGO_EXTENSIONS
    )
@app.route("/shop-settings", methods=["GET", "POST"])
def shop_settings():
    shop = get_shop_settings()

    if request.method == "POST":
        shop_name = request.form.get("shop_name", "").strip()
        owner_name = request.form.get("owner_name", "").strip()
        address = request.form.get("address", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        gstin = request.form.get("gstin", "").strip()

        if not shop_name:
            flash("Please enter your shop name.", "danger")
            return render_template(
                "shop_settings.html", shop=shop
            )

        # Keep the existing logo unless a new one is uploaded.
        logo_path = shop["logo_path"] or ""

        logo = request.files.get("shop_logo")

        if logo and logo.filename:
            if not allowed_shop_logo(logo.filename):
                flash(
                    "Upload a PNG, JPG, JPEG, or WEBP logo.",
                    "danger"
                )
                return render_template(
                    "shop_settings.html", shop=shop
                )

            extension = secure_filename(
                logo.filename
            ).rsplit(".", 1)[1].lower()

            filename = f"{uuid.uuid4().hex}.{extension}"
            save_path = os.path.join(
                SHOP_LOGO_FOLDER, filename
            )

            logo.save(save_path)
            logo_path = f"uploads/shop/{filename}"

        conn = get_shop_db_connection()

        conn.execute("""
            UPDATE shop_settings
            SET shop_name = ?,
                owner_name = ?,
                address = ?,
                phone = ?,
                email = ?,
                gstin = ?,
                logo_path = ?
            WHERE id = 1
        """, (
            shop_name,
            owner_name,
            address,
            phone,
            email,
            gstin,
            logo_path
        ))

        conn.commit()
        conn.close()

        flash("Shop details saved successfully!", "success")
        return redirect(url_for("shop_settings"))

    return render_template(
        "shop_settings.html", shop=shop
    )

@app.route('/billing/invoice/<int:sale_id>')
def view_invoice(sale_id):
    conn = database.get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM sales WHERE id = ?', (sale_id,))
    sale = cursor.fetchone()

    if not sale:
        flash('Invoice not found.', 'danger')
        conn.close()
        return redirect(url_for('sales'))

    cursor.execute('SELECT * FROM sale_items WHERE sale_id = ?', (sale_id,))
    items = cursor.fetchall()

    cursor.execute('SELECT * FROM warranties WHERE sale_id = ?', (sale_id,))
    warranties = cursor.fetchall()

    conn.close()

    return render_template('invoice_view.html', sale=sale, items=items, warranties=warranties)

@app.route('/billing/invoice/<int:sale_id>/pdf')
def download_invoice_pdf(sale_id):
    conn = database.get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM sales WHERE id = ?', (sale_id,))
    sale = cursor.fetchone()

    if not sale:
        conn.close()
        return "Invoice not found", 404

    cursor.execute('SELECT * FROM sale_items WHERE sale_id = ?', (sale_id,))
    items = cursor.fetchall()

    cursor.execute('SELECT * FROM warranties WHERE sale_id = ?', (sale_id,))
    warranties = cursor.fetchall()

    conn.close()

    # Convert row objects to dicts for pdf generator
    sale_dict = dict(sale)
    items_dict = [dict(i) for i in items]
    warranties_dict = [dict(w) for w in warranties]

    pdf_bytes = generate_invoice_pdf(sale_dict, items_dict, warranties_dict)

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"{sale['invoice_no']}.pdf"
    )

@app.route('/sales')
def sales():
    search = request.args.get('search', '').strip()
    payment_filter = request.args.get('payment_mode', '').strip()

    conn = database.get_db()
    cursor = conn.cursor()

    query = '''
        SELECT s.*, (SELECT COUNT(*) FROM sale_items WHERE sale_id = s.id) as item_count
        FROM sales s
        WHERE 1=1
    '''
    params = []

    if search:
        query += ' AND (customer_name LIKE ? OR customer_phone LIKE ? OR invoice_no LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])
    if payment_filter:
        query += ' AND payment_mode = ?'
        params.append(payment_filter)

    query += ' ORDER BY sale_date DESC'
    cursor.execute(query, params)
    sales_list = cursor.fetchall()

    # Calculate summary metrics
    cursor.execute('SELECT COALESCE(SUM(total_amount), 0), COALESCE(SUM(gst_amount), 0), COUNT(id) FROM sales')
    totals = cursor.fetchone()
    total_sales_revenue = totals[0]
    total_gst_collected = totals[1]
    total_invoices_count = totals[2]

    conn.close()

    return render_template(
        'sales.html',
        sales=sales_list,
        total_revenue=total_sales_revenue,
        total_gst=total_gst_collected,
        total_count=total_invoices_count,
        search=search,
        selected_payment=payment_filter
    )

@app.route('/warranty')
def warranty():
    query_str = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '').strip()

    conn = database.get_db()
    cursor = conn.cursor()

    sql = '''
        SELECT w.*, s.invoice_no
        FROM warranties w
        LEFT JOIN sales s ON w.sale_id = s.id
        WHERE 1=1
    '''
    params = []

    if query_str:
        sql += ' AND (w.serial_number LIKE ? OR w.customer_name LIKE ? OR w.customer_phone LIKE ? OR w.product_name LIKE ?)'
        params.extend([f'%{query_str}%', f'%{query_str}%', f'%{query_str}%', f'%{query_str}%'])
    if status_filter:
        sql += ' AND w.status = ?'
        params.append(status_filter)

    sql += ' ORDER BY w.id DESC'
    cursor.execute(sql, params)
    warranty_rows = cursor.fetchall()

    # Dynamic status calculator for display (Active, Expiring Soon, Expired)
    today_date = datetime.now().date()
    warranties_list = []

    for row in warranty_rows:
        w_dict = dict(row)
        exp_dt = datetime.strptime(w_dict['expiry_date'], '%Y-%m-%d').date()
        days_remaining = (exp_dt - today_date).days

        if w_dict['status'] != 'Replaced':
            if days_remaining < 0:
                calc_status = 'Expired'
            elif days_remaining <= 30:
                calc_status = 'Expiring Soon'
            else:
                calc_status = 'Active'
        else:
            calc_status = 'Replaced'

        w_dict['calculated_status'] = calc_status
        w_dict['days_remaining'] = days_remaining
        warranties_list.append(w_dict)

    conn.close()

    return render_template(
        'warranty.html',
        warranties=warranties_list,
        search_query=query_str,
        selected_status=status_filter
    )

@app.route('/warranty/update_status/<int:warranty_id>', methods=['POST'])
def update_warranty_status(warranty_id):
    status = request.form.get('status')
    notes = request.form.get('notes', '')

    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE warranties SET status = ?, notes = ? WHERE id = ?', (status, notes, warranty_id))
    conn.commit()
    conn.close()

    flash('Warranty record updated successfully!', 'success')
    return redirect(url_for('warranty'))

@app.route('/suppliers')
def suppliers():
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM suppliers ORDER BY name')
    suppliers_list = cursor.fetchall()
    conn.close()
    return render_template('suppliers.html', suppliers=suppliers_list)

@app.route('/suppliers/add', methods=['POST'])
def add_supplier():
    name = request.form['name']
    contact_person = request.form.get('contact_person', '')
    phone = request.form.get('phone', '')
    email = request.form.get('email', '')
    address = request.form.get('address', '')

    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO suppliers (name, contact_person, phone, email, address)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, contact_person, phone, email, address))
    conn.commit()
    conn.close()

    flash(f'Supplier "{name}" added successfully!', 'success')
    return redirect(url_for('suppliers'))



@app.route('/api/dashboard_data')
def dashboard_data_api():
    conn = database.get_db()
    cursor = conn.cursor()

    # Category totals
    cursor.execute('''
        SELECT category, COALESCE(SUM(stock_qty), 0) as stock
        FROM products
        GROUP BY category
    ''')
    cat_data = cursor.fetchall()

    # Brand totals
    cursor.execute('''
        SELECT brand, COALESCE(SUM(stock_qty), 0) as stock
        FROM products
        GROUP BY brand
    ''')
    brand_data = cursor.fetchall()

    conn.close()

    return jsonify({
        'categories': [r['category'] for r in cat_data],
        'category_stocks': [r['stock'] for r in cat_data],
        'brands': [r['brand'] for r in brand_data],
        'brand_stocks': [r['stock'] for r in brand_data]
    })

if __name__ == '__main__':
    print("Starting VoltTrack Battery Shop Management System...")
    app.run(debug=True, port=5000)