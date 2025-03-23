from flask import Flask, request, jsonify
import mysql.connector
import bcrypt

app = Flask(__name__)

# MySQL connection configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password':"z_maximal_optimal_prime@@789",
    'database': 'vericart'
}

# Function to get a new database connection for each request
def get_db_connection():
    conn = mysql.connector.connect(**db_config)
    print("Auto-commit status:", conn.autocommit)  # Should print True or False
    return conn
    return mysql.connector.connect(**db_config)

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data['username']
    password = data['password']
    email = data.get('email', '')

    # Hash the password
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password, email) VALUES (%s, %s, %s)", (username, hashed_password, email))
        conn.commit()
        return jsonify({"message": "User registered"}), 201
    except mysql.connector.Error as err:
        if err.errno == 1062:  # Duplicate entry
            return jsonify({"message": "Username already exists"}), 400
        return jsonify({"message": str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data['username']
    password = data['password']

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, password FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        if user and bcrypt.checkpw(password.encode('utf-8'), user[3].encode('utf-8')):
            return jsonify({"message": "Login successful", "user": {"id": user[0], "username": user[1], "email": user[2]}})
        return jsonify({"message": "Invalid credentials"}), 401
    except mysql.connector.Error as err:
        return jsonify({"message": str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/profile/<int:user_id>', methods=['GET', 'PUT'])
def manage_profile(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if request.method == 'GET':
            cursor.execute("SELECT username, email FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            if user:
                return jsonify({"username": user[0], "email": user[1]})
            return jsonify({"message": "User not found"}), 404
        elif request.method == 'PUT':
            data = request.get_json()
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')

            updates = []
            params = []
            if username:
                updates.append("username = %s")
                params.append(username)
            if email:
                updates.append("email = %s")
                params.append(email)
            if password:
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                updates.append("password = %s")
                params.append(hashed_password)

            if updates:
                params.append(user_id)
                query = f"UPDATE users SET {', '.join(updates)} WHERE id = %s"
                cursor.execute(query, params)
                conn.commit()
                return jsonify({"message": "Profile updated"})
            return jsonify({"message": "No fields to update"}), 400
    except mysql.connector.Error as err:
        if err.errno == 1062:  # Duplicate entry (e.g., username already exists)
            return jsonify({"message": "Username already exists"}), 400
        return jsonify({"message": str(err)}), 500
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)