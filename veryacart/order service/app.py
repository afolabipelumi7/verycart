from flask import Flask, request, jsonify
import mysql.connector
import pika
import json
import requests

app = Flask(__name__)

# MySQL connection configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password':' z_maximal_optimal_prime@@789',
    'database': 'vericart'
}

# Function to get a new database connection for each request
def get_db_connection():
    return mysql.connector.connect(**db_config)

# Function to publish a message to RabbitMQ
def publish_to_rabbitmq(message):
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        channel.queue_declare(queue='notifications')
        channel.basic_publish(exchange='', routing_key='notifications', body=json.dumps(message))
        connection.close()
    except pika.exceptions.AMQPConnectionError as err:
        print(f"RabbitMQ error: {err}")

@app.route('/orders', methods=['POST'])
def place_order():
    data = request.get_json()
    user_id = data.get('user_id')
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)  # Default to 1 if not provided

    # Validate input
    if not isinstance(user_id, int) or user_id <= 0:
        return jsonify({"message": "User ID must be a positive integer"}), 400
    if not isinstance(product_id, int) or product_id <= 0:
        return jsonify({"message": "Product ID must be a positive integer"}), 400
    if not isinstance(quantity, int) or quantity <= 0:
        return jsonify({"message": "Quantity must be a positive integer"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if the user exists
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cursor.fetchone():
            return jsonify({"message": "User not found"}), 404

        # Check if the product exists and has enough stock
        cursor.execute("SELECT stock, price FROM products WHERE id = %s", (product_id,))
        product = cursor.fetchone()
        if not product:
            return jsonify({"message": "Product not found"}), 404
        stock, price = product
        if stock < quantity:
            return jsonify({"message": "Insufficient stock"}), 400

        # Calculate the payment amount
        amount = price * quantity

        # Create the order
        cursor.execute(
            "INSERT INTO orders (user_id, product_id, quantity, status, payment_status) VALUES (%s, %s, %s, %s, %s)",
            (user_id, product_id, quantity, "Pending", "Pending")
        )
        conn.commit()
        order_id = cursor.lastrowid

        # Process payment
        try:
            payment_response = requests.post(
                "http://localhost:5003/pay",  # Correct URL for local setup
                json={"order_id": order_id, "amount": amount}
            )
            if payment_response.status_code == 200:
                cursor.execute("UPDATE orders SET payment_status = 'Paid' WHERE id = %s", (order_id,))
                conn.commit()
                # Reduce stock
                cursor.execute("UPDATE products SET stock = stock - %s WHERE id = %s", (quantity, product_id))
                conn.commit()
                # Send notification
                message = {"order_id": order_id, "status": "Pending", "user_id": user_id}
                publish_to_rabbitmq(message)
                return jsonify({"message": "Order placed", "order_id": order_id}), 201
            return jsonify({"message": "Payment failed"}), 400
        except requests.exceptions.RequestException as err:
            return jsonify({"message": f"Payment service error: {str(err)}"}), 500

    except mysql.connector.Error as err:
        return jsonify({"message": str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/orders/<int:order_id>', methods=['PUT'])
def process_order(order_id):
    data = request.get_json()
    status = data.get('status')

    # Validate status
    valid_statuses = ["Pending", "Shipped", "Delivered", "Cancelled"]
    if not status or status not in valid_statuses:
        return jsonify({"message": f"Status must be one of {valid_statuses}"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if the order exists
        cursor.execute("SELECT user_id FROM orders WHERE id = %s", (order_id,))
        order = cursor.fetchone()
        if not order:
            return jsonify({"message": "Order not found"}), 404
        user_id = order[0]

        # Update the order status
        cursor.execute("UPDATE orders SET status = %s WHERE id = %s", (status, order_id))
        conn.commit()

        # Send notification
        message = {"order_id": order_id, "status": status, "user_id": user_id}
        publish_to_rabbitmq(message)

        return jsonify({"message": "Order updated"})

    except mysql.connector.Error as err:
        return jsonify({"message": str(err)}), 500
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)  # Correct port for order_service