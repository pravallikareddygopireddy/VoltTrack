import sqlite3
import os
from datetime import datetime, timedelta
import random

DB_FILE = 'volttrack.db'

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Products Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        brand TEXT NOT NULL,
        model TEXT NOT NULL,
        category TEXT NOT NULL,
        capacity TEXT NOT NULL,
        voltage TEXT DEFAULT '12V',
        warranty_months INTEGER DEFAULT 24,
        purchase_price REAL NOT NULL,
        selling_price REAL NOT NULL,
        stock_qty INTEGER NOT NULL DEFAULT 0,
        min_stock_alert INTEGER DEFAULT 5,
        supplier_name TEXT,
        supplier_phone TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 2. Sales Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_no TEXT UNIQUE NOT NULL,
        customer_name TEXT NOT NULL,
        customer_phone TEXT NOT NULL,
        customer_address TEXT,
        sale_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        subtotal REAL NOT NULL,
        gst_rate REAL DEFAULT 18.0,
        gst_amount REAL NOT NULL,
        old_battery_rebate REAL DEFAULT 0.0,
        total_amount REAL NOT NULL,
        payment_mode TEXT DEFAULT 'Cash'
    )
    ''')

    # 3. Sale Items Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sale_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        product_name TEXT NOT NULL,
        brand TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        total_price REAL NOT NULL,
        FOREIGN KEY (sale_id) REFERENCES sales (id),
        FOREIGN KEY (product_id) REFERENCES products (id)
    )
    ''')

    # 4. Warranty Tracking Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS warranties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        product_name TEXT NOT NULL,
        customer_name TEXT NOT NULL,
        customer_phone TEXT NOT NULL,
        serial_number TEXT UNIQUE NOT NULL,
        purchase_date DATE NOT NULL,
        warranty_months INTEGER NOT NULL,
        expiry_date DATE NOT NULL,
        status TEXT DEFAULT 'Active',
        notes TEXT,
        FOREIGN KEY (sale_id) REFERENCES sales (id),
        FOREIGN KEY (product_id) REFERENCES products (id)
    )
    ''')

    # 5. Suppliers Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact_person TEXT,
        phone TEXT,
        email TEXT,
        address TEXT
    )
    ''')

    conn.commit()

    # Seed initial data if products table is empty
    cursor.execute('SELECT COUNT(*) FROM products')
    count = cursor.fetchone()[0]
    if count == 0:
        seed_sample_data(conn)

    conn.close()

def seed_sample_data(conn):
    cursor = conn.cursor()
    
    # 1. Seed Suppliers
    suppliers = [
        ("South Zone Battery Agency", "Rajesh Kumar", "+91 98765 43210", "sales@southzonebatteries.in", "12 Industrial Estate, MG Road, Hyderabad"),
        ("Exide Power Distributors", "Venkatesh Rao", "+91 91234 56789", "orders@exidedist.com", "45 Auto Nagar, Vijayawada"),
        ("Amaron Care Hub", "Suresh Sharma", "+91 99887 76655", "hub@amaronpower.com", "88 Ring Road, Bengaluru"),
        ("Luminous Solar & Inverter Hub", "Anand Verma", "+91 94400 11223", "anand@luminousdirect.in", "102 Tech Park, Chennai")
    ]
    cursor.executemany('''
        INSERT INTO suppliers (name, contact_person, phone, email, address)
        VALUES (?, ?, ?, ?, ?)
    ''', suppliers)

    # 2. Seed Battery Products
    # Categories: Vehicle Batteries, Two-wheeler Batteries, Inverter Batteries, Other Battery types
    products = [
        # Vehicle Batteries
        ("Exide Matrix Red 35Ah", "Exide", "MTRED35L", "Vehicle Batteries", "35 Ah", "12V", 36, 3200.0, 4100.0, 15, 4, "Exide Power Distributors", "+91 91234 56789"),
        ("Amaron FLO 55Ah DIN55", "Amaron", "AAM-FL-555112060", "Vehicle Batteries", "55 Ah", "12V", 48, 5100.0, 6400.0, 18, 5, "Amaron Care Hub", "+91 99887 76655"),
        ("Exide Mileage 100Ah", "Exide", "FMI0-MRED100", "Vehicle Batteries", "100 Ah", "12V", 24, 6800.0, 8500.0, 12, 3, "Exide Power Distributors", "+91 91234 56789"),
        ("SF Sonic Flash 65Ah", "SF Sonic", "FSH65L", "Vehicle Batteries", "65 Ah", "12V", 36, 4400.0, 5600.0, 8, 3, "South Zone Battery Agency", "+91 98765 43210"),
        ("Tata Green YUASA 80Ah", "Tata Green", "TG800R", "Vehicle Batteries", "80 Ah", "12V", 36, 5900.0, 7200.0, 2, 4, "South Zone Battery Agency", "+91 98765 43210"), # Low stock item
        
        # Two-wheeler Batteries
        ("Amaron Rider Beta 5Ah", "Amaron", "ABR-PR-APTZ5L", "Two-wheeler Batteries", "5 Ah", "12V", 24, 950.0, 1350.0, 25, 6, "Amaron Care Hub", "+91 99887 76655"),
        ("Exide Xplode 2.5Ah", "Exide", "FXP0-XLTZ4", "Two-wheeler Batteries", "2.5 Ah", "12V", 18, 720.0, 1050.0, 20, 5, "Exide Power Distributors", "+91 91234 56789"),
        ("Exide Bikerz 9Ah", "Exide", "BKR-12V9AH", "Two-wheeler Batteries", "9 Ah", "12V", 24, 1400.0, 1950.0, 3, 5, "Exide Power Distributors", "+91 91234 56789"), # Low stock item
        ("Amaron Pro Bike Rider 7Ah", "Amaron", "ABR-PR-APTZ7L", "Two-wheeler Batteries", "7 Ah", "12V", 36, 1250.0, 1750.0, 14, 4, "Amaron Care Hub", "+91 99887 76655"),

        # Inverter Batteries
        ("Luminous Red Charge 150Ah Tubular", "Luminous", "RC18000ST", "Inverter Batteries", "150 Ah", "12V", 36, 9500.0, 12800.0, 10, 4, "Luminous Solar & Inverter Hub", "+91 94400 11223"),
        ("Exide Inva Tubular 200Ah", "Exide", "IT500", "Inverter Batteries", "200 Ah", "12V", 48, 12500.0, 16200.0, 7, 3, "Exide Power Distributors", "+91 91234 56789"),
        ("Microtek Okaya 160Ah Tall Tubular", "Microtek", "OPTT19060", "Inverter Batteries", "160 Ah", "12V", 36, 10200.0, 13500.0, 1, 3, "Luminous Solar & Inverter Hub", "+91 94400 11223"), # Low stock item
        ("Amaron Tall Tubular 150Ah", "Amaron", "CR-AR150TT", "Inverter Batteries", "150 Ah", "12V", 36, 9800.0, 13100.0, 9, 3, "Amaron Care Hub", "+91 99887 76655"),

        # Other Battery types (UPS, Solar, E-Rickshaw)
        ("Exide PowerSafe 12V 42Ah SMF UPS", "Exide", "EP42-12", "Other Battery types", "42 Ah", "12V", 24, 3800.0, 4900.0, 11, 3, "Exide Power Distributors", "+91 91234 56789"),
        ("Luminous Solar C10 100Ah", "Luminous", "LPTT12100H", "Other Battery types", "100 Ah", "12V", 60, 8900.0, 11500.0, 6, 2, "Luminous Solar & Inverter Hub", "+91 94400 11223"),
        ("Amara Raja E-Rickshaw 120Ah", "Amaron", "ER1200", "Other Battery types", "120 Ah", "12V", 18, 6500.0, 8400.0, 2, 4, "Amaron Care Hub", "+91 99887 76655") # Low stock item
    ]

    cursor.executemany('''
        INSERT INTO products (name, brand, model, category, capacity, voltage, warranty_months, purchase_price, selling_price, stock_qty, min_stock_alert, supplier_name, supplier_phone)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', products)

    # 3. Seed Sample Sales & Warranties
    # Sample Sale 1 (Matches user request example!)
    # Customer: Rahul, Exide 12V 100Ah, Qty: 1, Price: ₹8,500, GST: ₹1,530, Total: ₹10,030
    today = datetime.now()
    date_str = today.strftime('%Y-%m-%d %H:%M:%S')
    date_only = today.strftime('%Y-%m-%d')
    expiry_24m = (today + timedelta(days=24*30)).strftime('%Y-%m-%d')
    expiry_36m = (today + timedelta(days=36*30)).strftime('%Y-%m-%d')
    past_expired = (today - timedelta(days=10)).strftime('%Y-%m-%d')

    # Sale 1 (Rahul - Today)
    cursor.execute('''
        INSERT INTO sales (invoice_no, customer_name, customer_phone, customer_address, sale_date, subtotal, gst_rate, gst_amount, old_battery_rebate, total_amount, payment_mode)
        VALUES ('INV-2026-0001', 'Rahul Sharma', '+91 98765 12345', 'Plot 40, Cyber Towers, Hyderabad', ?, 8500.0, 18.0, 1530.0, 0.0, 10030.0, 'UPI')
    ''', (date_str,))
    sale1_id = cursor.lastrowid

    cursor.execute('''
        INSERT INTO sale_items (sale_id, product_id, product_name, brand, quantity, unit_price, total_price)
        VALUES (?, 3, 'Exide Mileage 100Ah', 'Exide', 1, 8500.0, 8500.0)
    ''', (sale1_id,))

    cursor.execute('''
        INSERT INTO warranties (sale_id, product_id, product_name, customer_name, customer_phone, serial_number, purchase_date, warranty_months, expiry_date, status, notes)
        VALUES (?, 3, 'Exide Mileage 100Ah', 'Rahul Sharma', '+91 98765 12345', 'EX-2026-88491', ?, 24, ?, 'Active', 'Sold with original bill')
    ''', (sale1_id, date_only, expiry_24m))

    # Sale 2 (Priya Patel - Today)
    cursor.execute('''
        INSERT INTO sales (invoice_no, customer_name, customer_phone, customer_address, sale_date, subtotal, gst_rate, gst_amount, old_battery_rebate, total_amount, payment_mode)
        VALUES ('INV-2026-0002', 'Priya Patel', '+91 99123 44556', 'H.No 12-4, Park Street, Hyderabad', ?, 25600.0, 18.0, 4608.0, 1500.0, 28708.0, 'Credit Card')
    ''', (date_str,))
    sale2_id = cursor.lastrowid

    cursor.execute('''
        INSERT INTO sale_items (sale_id, product_id, product_name, brand, quantity, unit_price, total_price)
        VALUES (?, 10, 'Luminous Red Charge 150Ah Tubular', 'Luminous', 2, 12800.0, 25600.0)
    ''', (sale2_id,))

    cursor.execute('''
        INSERT INTO warranties (sale_id, product_id, product_name, customer_name, customer_phone, serial_number, purchase_date, warranty_months, expiry_date, status, notes)
        VALUES (?, 10, 'Luminous Red Charge 150Ah Tubular', 'Priya Patel', '+91 99123 44556', 'LUM-INV-99401', ?, 36, ?, 'Active', 'Dual inverter battery setup')
    ''', (sale2_id, date_only, expiry_36m))

    cursor.execute('''
        INSERT INTO warranties (sale_id, product_id, product_name, customer_name, customer_phone, serial_number, purchase_date, warranty_months, expiry_date, status, notes)
        VALUES (?, 10, 'Luminous Red Charge 150Ah Tubular', 'Priya Patel', '+91 99123 44556', 'LUM-INV-99402', ?, 36, ?, 'Active', 'Dual inverter battery setup')
    ''', (sale2_id, date_only, expiry_36m))

    # Sale 3 (Vikram Reddy - Past Sale for Warranty Testing)
    past_date = (today - timedelta(days=740)).strftime('%Y-%m-%d %H:%M:%S')
    past_purch_date = (today - timedelta(days=740)).strftime('%Y-%m-%d')
    cursor.execute('''
        INSERT INTO sales (invoice_no, customer_name, customer_phone, customer_address, sale_date, subtotal, gst_rate, gst_amount, old_battery_rebate, total_amount, payment_mode)
        VALUES ('INV-2024-0089', 'Vikram Reddy', '+91 94900 88776', 'Banjara Hills, Hyderabad', ?, 6400.0, 18.0, 1152.0, 500.0, 7052.0, 'Cash')
    ''', (past_date,))
    sale3_id = cursor.lastrowid

    cursor.execute('''
        INSERT INTO sale_items (sale_id, product_id, product_name, brand, quantity, unit_price, total_price)
        VALUES (?, 2, 'Amaron FLO 55Ah DIN55', 'Amaron', 1, 6400.0, 6400.0)
    ''', (sale3_id,))

    cursor.execute('''
        INSERT INTO warranties (sale_id, product_id, product_name, customer_name, customer_phone, serial_number, purchase_date, warranty_months, expiry_date, status, notes)
        VALUES (?, 2, 'Amaron FLO 55Ah DIN55', 'Vikram Reddy', '+91 94900 88776', 'AMR-FL-33019', ?, 24, ?, 'Expired', 'Warranty expired 10 days ago')
    ''', (sale3_id, past_purch_date, past_expired))

    conn.commit()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully!")
