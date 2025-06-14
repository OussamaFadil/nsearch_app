# auth_functions.py
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

def register_user(username, password, email, full_name):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    try:
        c.execute("INSERT INTO users (username, password, email, full_name) VALUES (?, ?, ?, ?)",
                  (username, hashed_password, email, full_name))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def authenticate_user(username, password):
    #print(username, password)
    #print('salamo alaikom')
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username=?", (username,))
    # c.execute("SELECT *FROM users ")
    result = c.fetchone()
    # result = c.fetchall()
    # print(result[0])
    conn.close()
    if result and check_password_hash(result[0], password):
        return True
    return False
