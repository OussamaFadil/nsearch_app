# setup_database.py
import sqlite3

def setup_database():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Création de la table des utilisateurs
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE,
                  password TEXT,
                  email TEXT,
                  full_name TEXT)''')

    conn.commit()
    conn.close()

if __name__ == "__main__":
    setup_database()
