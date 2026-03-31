from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import re # <-- IMPORT PYTHON REGEX

app = Flask(__name__)
CORS(app)

# ------------------ DB CONNECTION ------------------
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",        # Change if your MySQL user is different
        password="root",    # Change if your MySQL password is different
        database="whiff_whisk"
    )

# --- BACKEND REGEX VALIDATION HELPERS ---
def is_valid_email(email):
    return re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email) is not None

def is_valid_phone(phone):
    return re.match(r"^\+?[\d\s-]{10,}$", phone) is not None

@app.route('/', methods=['GET'])
def home():
    return "Backend Running!"

# =====================================================
# 👤 CUSTOMERS & REGISTRATION (Now with Backend Security)
# =====================================================
@app.route('/customers', methods=['GET', 'POST'])
def customers():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'GET':
        cursor.execute("SELECT customer_id, name, email, phone, address FROM customers")
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(data)
        
    if request.method == 'POST':
        data = request.json
        
        # 1. API-LEVEL SECURITY CHECKS
        if not is_valid_email(data.get('email', '')):
            return jsonify({"error": "Invalid email format rejected by server."}), 400
        if not is_valid_phone(data.get('phone', '')):
            return jsonify({"error": "Invalid phone format rejected by server."}), 400

        hashed_password = generate_password_hash(data['password']) 
        
        try:
            cursor.execute("""
                INSERT INTO customers (name, email, phone, address, password)
                VALUES (%s, %s, %s, %s, %s)
            """, (data['name'], data['email'], data['phone'], data['address'], hashed_password))
            conn.commit()
            return jsonify({"message": "Customer added successfully!"}), 201
        except mysql.connector.Error as err:
            return jsonify({"error": str(err)}), 400
        finally:
            cursor.close()
            conn.close()

@app.route('/customers/<int:id>', methods=['PUT', 'DELETE'])
def modify_customer(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'PUT':
        data = request.json
        
        # 2. API-LEVEL SECURITY CHECKS FOR UPDATES
        if not is_valid_email(data.get('email', '')):
            return jsonify({"error": "Invalid email format rejected by server."}), 400
        if not is_valid_phone(data.get('phone', '')):
            return jsonify({"error": "Invalid phone format rejected by server."}), 400

        try:
            cursor.execute("""
                UPDATE customers 
                SET name=%s, email=%s, phone=%s, address=%s
                WHERE customer_id=%s
            """, (data['name'], data['email'], data['phone'], data['address'], id))
            conn.commit()
            return jsonify({"message": "Customer updated!"})
        except mysql.connector.Error as err:
            return jsonify({"error": str(err)}), 400
        finally:
            cursor.close()
            conn.close()

    if request.method == 'DELETE':
        try:
            cursor.execute("DELETE FROM customers WHERE customer_id = %s", (id,))
            conn.commit()
            return jsonify({"message": "Customer deleted!"})
        except mysql.connector.Error as err:
            if err.errno == 1451:
                return jsonify({"error": "Cannot delete a customer with active order history."}), 400
            return jsonify({"error": str(err)}), 400
        finally:
            cursor.close()
            conn.close()

# =====================================================
# 🛡️ STAFF / ADMINS
# =====================================================
@app.route('/staff', methods=['POST'])
def register_staff():
    data = request.json
    
    # API-LEVEL CHECK
    if not is_valid_email(data.get('email', '')):
        return jsonify({"error": "Invalid email format rejected by server."}), 400

    hashed_password = generate_password_hash(data['password']) 
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO staff (name, email, password)
            VALUES (%s, %s, %s)
        """, (data['name'], data['email'], hashed_password))
        conn.commit()
        return jsonify({"message": "Staff member registered successfully!"}), 201
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 400
    finally:
        cursor.close()
        conn.close()

# =====================================================
# 📦 PRODUCTS 
# =====================================================
@app.route('/products', methods=['GET', 'POST'])
def products():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'GET':
        cursor.execute("SELECT * FROM products")
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(data)

    if request.method == 'POST':
        data = request.json
        cursor.execute("""
            INSERT INTO products (name, price, stock_quantity, category)
            VALUES (%s, %s, %s, %s)
        """, (data['name'], data['price'], data['stock_quantity'], data['category']))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Product added successfully!"})

@app.route('/products/<int:id>', methods=['PUT', 'DELETE'])
def modify_product(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'PUT':
        data = request.json
        try:
            cursor.execute("""
                UPDATE products 
                SET name=%s, price=%s, stock_quantity=%s, category=%s
                WHERE product_id=%s
            """, (data['name'], data['price'], data['stock_quantity'], data['category'], id))
            conn.commit()
            return jsonify({"message": "Product updated!"})
        except mysql.connector.Error as err:
            return jsonify({"error": str(err)}), 400
        finally:
            cursor.close()
            conn.close()

    if request.method == 'DELETE':
        try:
            cursor.execute("DELETE FROM products WHERE product_id = %s", (id,))
            conn.commit()
            return jsonify({"message": "Product deleted!"})
        except mysql.connector.Error as err:
            if err.errno == 1451:
                return jsonify({"error": "Cannot delete this product because it has active order history."}), 400
            return jsonify({"error": str(err)}), 400
        finally:
            cursor.close()
            conn.close()

# =====================================================
# 🧾 ORDERS 
# =====================================================
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'GET':
        cursor.execute("""
            SELECT 
                o.order_id,
                c.name AS customer_name,
                GROUP_CONCAT(CONCAT(oi.quantity, 'x ', p.name) SEPARATOR ', ') AS ordered_items,
                o.total_amount,
                o.status,
                DATE_FORMAT(o.order_date, '%b %d, %Y') AS formatted_date
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            LEFT JOIN order_items oi ON o.order_id = oi.order_id
            LEFT JOIN products p ON oi.product_id = p.product_id
            GROUP BY o.order_id
            ORDER BY o.order_date DESC
        """)
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(data)

    if request.method == 'POST':
        data = request.json
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO orders (customer_id, total_amount, status)
            VALUES (%s, %s, %s)
        """, (data['customer_id'], data['total_amount'], "Placed"))
        order_id = cursor.lastrowid

        for item in data['items']:
            cursor.execute("""
                INSERT INTO order_items (order_id, product_id, quantity, price)
                VALUES (%s, %s, %s, %s)
            """, (order_id, item['product_id'], item['quantity'], item['price']))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Order created successfully!"})

# =====================================================
# 🌾 INGREDIENTS
# =====================================================
@app.route('/ingredients', methods=['GET', 'POST'])
def ingredients():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'GET':
        cursor.execute("SELECT * FROM ingredients")
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(data)
        
    if request.method == 'POST':
        data = request.json
        cursor.execute("INSERT INTO ingredients (name, stock_quantity, unit) VALUES (%s, %s, %s)", 
                       (data['name'], data['stock_quantity'], data['unit']))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Ingredient added!"})

@app.route('/ingredients/<int:id>', methods=['PUT', 'DELETE'])
def modify_ingredient(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'PUT':
        data = request.json
        cursor.execute("UPDATE ingredients SET name=%s, stock_quantity=%s, unit=%s WHERE ingredient_id=%s", 
                       (data['name'], data['stock_quantity'], data['unit'], id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Ingredient updated!"})
        
    if request.method == 'DELETE':
        cursor.execute("DELETE FROM ingredients WHERE ingredient_id = %s", (id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Ingredient deleted!"})

# =====================================================
# 🚚 SUPPLIERS
# =====================================================
@app.route('/suppliers', methods=['GET', 'POST'])
def suppliers():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'GET':
        cursor.execute("SELECT * FROM suppliers")
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(data)
        
    if request.method == 'POST':
        data = request.json
        cursor.execute("INSERT INTO suppliers (name, contact, email) VALUES (%s, %s, %s)", 
                       (data['name'], data['contact'], data['email']))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Supplier added!"})

@app.route('/suppliers/<int:id>', methods=['PUT', 'DELETE'])
def modify_supplier(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'PUT':
        data = request.json
        cursor.execute("UPDATE suppliers SET name=%s, contact=%s, email=%s WHERE supplier_id=%s", 
                       (data['name'], data['contact'], data['email'], id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Supplier updated!"})
        
    if request.method == 'DELETE':
        cursor.execute("DELETE FROM suppliers WHERE supplier_id = %s", (id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Supplier deleted!"})

# =====================================================
# 📊 ANALYTICS (Aggregates & Views)
# =====================================================
@app.route('/api/stats', methods=['GET'])
def get_stats():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT 
            COUNT(order_id) as total_orders, 
            COALESCE(SUM(total_amount), 0) as total_revenue,
            COALESCE(AVG(total_amount), 0) as avg_order_value
        FROM orders
    """)
    summary = cursor.fetchone()
    
    cursor.execute("SELECT * FROM daily_sales")
    sales_history = cursor.fetchall()

    cursor.execute("SELECT * FROM products WHERE stock_quantity < 15")
    low_stock = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return jsonify({
        "summary": summary,
        "sales_history": sales_history,
        "alerts": low_stock
    })

# =====================================================
# 🔐 AUTHENTICATION LOGIC
# =====================================================
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    role = data.get('role')
    email = data.get('email')
    password = data.get('password')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if role == 'admin':
        cursor.execute("SELECT * FROM staff WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if user and check_password_hash(user['password'], password):
            return jsonify({"message": "Admin login successful", "user": {"id": user['staff_id'], "name": user['name']}}), 200
        else:
            return jsonify({"error": "Invalid admin credentials. Please try again."}), 401
            
    elif role == 'customer':
        cursor.execute("SELECT * FROM customers WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            return jsonify({"message": "Login successful", "user": {"id": user['customer_id'], "name": user['name']}}), 200
        else:
            return jsonify({"error": "Invalid email or password. Please try again."}), 401

    cursor.close()
    conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)