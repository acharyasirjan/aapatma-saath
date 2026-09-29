import sqlite3
from werkzeug.security import generate_password_hash


DATABASE = "data/users.db"


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():

    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()
    connection.close()


def create_user(full_name, username, email, password):

    connection = get_connection()

    try:

        hashed_password = generate_password_hash(password)

        connection.execute("""
            INSERT INTO users
            (full_name, username, email, password)
            VALUES (?, ?, ?, ?)
        """, (
            full_name,
            username,
            email,
            hashed_password
        ))

        connection.commit()

        return True

    except sqlite3.IntegrityError:

        return False

    finally:

        connection.close()