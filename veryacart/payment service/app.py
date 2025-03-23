from flask import Flask, request, jsonify
import mysql.connector
import random

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

@app.route('/pay', methods=['POST'])
def process_payment():
    data = request.get_json()
    order_id = data.get('order_id')
    amount = data.get('amount')

    # Validate input
    if not isinstance(order_id, int) or order_id <= 0:
        return jsonify({"message": "Order ID must be a positive integer"}), 400
    if not isinstance(amount, (int, float)) or amount <= 0:
        return jsonify({"message": "Amount must be a positive number"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if the order exists
        cursor.execute("SELECT user_id FROM orders WHERE id = %s", (order_id,))
        order = cursor.fetchone()
        if not order:
            return jsonify({"message": "Order not found"}), 404

        # Simulate payment processing (replace with real payment gateway integration in production)
        payment_status = "completed" if random.choice([True, False]) else "failed"

        # Store the payment in the database
        cursor.execute(
            "INSERT INTO payments (order_id, amount, status) VALUES (%s, %s, %s)",
            (order_id, amount, payment_status)
        )
        conn.commit()

        if payment_status == "completed":
            return jsonify({"message": "Payment successful", "order_id": order_id}), 200
        return jsonify({"message": "Payment failed"}), 400

    except mysql.connector.Error as err:
        return jsonify({"message": str(err)}), 500
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003)  # Correct port for payment_service