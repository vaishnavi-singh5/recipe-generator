import hashlib
import os
import sqlite3
from typing import Dict, List, Optional, Tuple


def init_db(db_path: Optional[str] = None) -> str:
    db_path = db_path or os.path.join(os.path.dirname(__file__), "recipe_app.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS saved_recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            title TEXT NOT NULL,
            recipe_text TEXT NOT NULL,
            ingredients TEXT NOT NULL,
            cuisine TEXT NOT NULL,
            diet TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()
    return db_path


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def register_user(username: str, password: str, db_path: Optional[str] = None) -> Dict[str, object]:
    db_path = db_path or init_db()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        (username.strip(), _hash_password(password)),
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return {"id": user_id, "username": username.strip()}


def authenticate_user(username: str, password: str, db_path: Optional[str] = None) -> bool:
    db_path = db_path or init_db()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT password_hash FROM users WHERE username = ?",
        (username.strip(),),
    )
    row = cursor.fetchone()
    conn.close()
    return bool(row and row[0] == _hash_password(password))


def save_recipe(
    username: str,
    title: str,
    recipe_text: str,
    ingredients: str,
    cuisine: str,
    diet: str,
    db_path: Optional[str] = None,
) -> bool:
    db_path = db_path or init_db()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO saved_recipes (username, title, recipe_text, ingredients, cuisine, diet)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (username.strip(), title, recipe_text, ingredients, cuisine, diet),
    )
    conn.commit()
    conn.close()
    return True


def get_saved_recipes(username: str, db_path: Optional[str] = None) -> List[Dict[str, object]]:
    db_path = db_path or init_db()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT title, recipe_text, ingredients, cuisine, diet FROM saved_recipes WHERE username = ? ORDER BY id DESC",
        (username.strip(),),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "title": row[0],
            "recipe_text": row[1],
            "ingredients": row[2],
            "cuisine": row[3],
            "diet": row[4],
        }
        for row in rows
    ]
