from flask import Flask, request, jsonify
import mysql.connector

app = Flask(__name__)

# MySQL connection configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'z_maximal_optimal_prime@@789',
    'database': 'vericart'
}

# Function to get a new database connection for each request
def get_db_connection():
    return mysql.connector.connect(**db_config)

@app.route('/products', methods=['POST'])
def add_product():
    data = request.get_json()
    name = data.get('name')
    price = data.get('price')
    stock = data.get('stock', 0)

    # Validate required fields
    if not name or not isinstance(name, str):
        return jsonify({"message": "Name is required and must be a string"}), 400
    if not isinstance(price, (int, float)) or price <= 0:
        return jsonify({"message": "Price is required and must be a positive number"}), 400
    if not isinstance(stock, int) or stock < 0:
        return jsonify({"message": "Stock must be a non-negative integer"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO products (name, price, stock) VALUES (%s, %s, %s)", (name, price, stock))
        conn.commit()
        product_id = cursor.lastrowid
        return jsonify({"message": "Product added", "id": product_id}), 201
    except mysql.connector.Error as err:
        return jsonify({"message": str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/products', methods=['GET'])
def get_products():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, price, stock FROM products")
        products = cursor.fetchall()
        return jsonify([{"id": p[0], "name": p[1], "price": p[2], "stock": p[3]} for p in products])
    except mysql.connector.Error as err:
        return jsonify({"message": str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/products/<int:product_id>', methods=['PUT', 'DELETE'])
def manage_product(product_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if the product exists
        cursor.execute("SELECT id FROM products WHERE id = %s", (product_id,))
        product = cursor.fetchone()
        if not product:
            return jsonify({"message": "Product not found"}), 404

        if request.method == 'PUT':
            data = request.get_json()
            name = data.get('name')
            price = data.get('price')
            stock = data.get('stock')

            # Validate provided fields
            updates = []
            params = []
            if name is not None:
                if not isinstance(name, str) or not name.strip():
                    return jsonify({"message": "Name must be a non-empty string"}), 400
                updates.append("name = %s")
                params.append(name)
            if price is not None:
                if not isinstance(price, (int, float)) or price <= 0:
                    return jsonify({"message": "Price must be a positive number"}), 400
                updates.append("price = %s")
                params.append(price)
            if stock is not None:
                if not isinstance(stock, int) or stock < 0:
                    return jsonify({"message": "Stock must be a non-negative integer"}), 400
                updates.append("stock = %s")
                params.append(stock)

            # Ensure at least one field is provided for update
            if not updates:
                return jsonify({"message": "No fields to update"}), 400

            # Update the product
            params.append(product_id)
            query = f"UPDATE products SET {', '.join(updates)} WHERE id = %s"
            cursor.execute(query, params)
            conn.commit()
            return jsonify({"message": "Product updated"})

        elif request.method == 'DELETE':
            cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
            conn.commit()
            return jsonify({"message": "Product deleted"})

    except mysql.connector.Error as err:
        return jsonify({"message": str(err)}), 500
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)  # Correct port for product_service