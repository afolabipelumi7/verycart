import mysql.connector
import pika
import json

# MySQL connection configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'z_maximal_optimal_prime@@789',
    'database': 'vericart'
}

# Function to get a new database connection
def get_db_connection():
    return mysql.connector.connect(**db_config)

def callback(ch, method, properties, body):
    try:
        # Parse the message
        message = json.loads(body)
        order_id = message['order_id']
        status = message['status']
        user_id = message['user_id']

        # Create the notification message
        notification_message = f"Order {order_id} status updated to {status}"

        # Store the notification in the database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO notifications (user_id, order_id, message) VALUES (%s, %s, %s)",
            (user_id, order_id, notification_message)
        )
        conn.commit()
        cursor.close()
        conn.close()

        # Print the notification for logging
        print(f"Notification for user {user_id}: {notification_message}")

    except json.JSONDecodeError as err:
        print(f"JSON parsing error: {err}")
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
    except KeyError as err:
        print(f"Missing field in message: {err}")

def main():
    while True:
        try:
            # Connect to RabbitMQ
            connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
            channel = connection.channel()
            channel.queue_declare(queue='notifications')

            # Start consuming messages
            channel.basic_consume(queue='notifications', on_message_callback=callback, auto_ack=True)
            print("Notification service running...")
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError as err:
            print(f"RabbitMQ connection error: {err}. Retrying in 5 seconds...")
            import time
            time.sleep(5)  # Wait before retrying
        except KeyboardInterrupt:
            print("Shutting down notification service...")
            break

if __name__ == '__main__':
    main()