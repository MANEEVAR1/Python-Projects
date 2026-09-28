import sqlite3
import time
import os
from contextlib import contextmanager

DB_PATH = os.environ.get("DATABASE_PATH", "notes.db")

@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                userId INTEGER PRIMARY KEY,
                userName TEXT UNIQUE NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users_notes (
                notesId INTEGER PRIMARY KEY,
                notes TEXT,
                timestamp TEXT,
                userId INTEGER,
                FOREIGN KEY (userId) REFERENCES users(userId)
            )
        """)
        cursor.execute("PRAGMA foreign_keys = ON;")

def create_note(user_id, user_name, notes_id, notes, timestamp):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT userName FROM users WHERE userId = ?", (user_id,))
            data = cursor.fetchone()
            if data and data["userName"] != user_name:
                return {"success": False, "message": f"UserId {user_id} is already assigned to someone else."}
            cursor.execute("INSERT OR IGNORE INTO users VALUES (?, ?)", (user_id, user_name))
            cursor.execute(
                "INSERT INTO users_notes VALUES (?, ?, ?, ?)",
                (notes_id, notes, timestamp, user_id)
            )
        return {"success": True, "message": "Note created successfully!", "notesId": notes_id}
    except sqlite3.IntegrityError:
        return {"success": False, "message": f"Username '{user_name}' already exists. Please choose a different one."}
    except Exception as e:
        return {"success": False, "message": f"Database error: {str(e)}"}

def read_note(notes_id):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT notes, timestamp, userId FROM users_notes WHERE notesId = ?", (notes_id,))
            data = cursor.fetchone()
            if data is None:
                return {"success": False, "message": f"No note found with NoteId #{notes_id}"}
            return {
                "success": True,
                "notes": data["notes"],
                "timestamp": data["timestamp"],
                "userId": data["userId"],
                "notesId": notes_id
            }
    except Exception as e:
        return {"success": False, "message": f"Database error: {str(e)}"}

def update_note(notes_id, notes):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT notesId FROM users_notes WHERE notesId = ?", (notes_id,))
            data = cursor.fetchone()
            if data is None:
                return {"success": False, "message": f"No note found with NoteId #{notes_id}"}
            cursor.execute("UPDATE users_notes SET notes = ? WHERE notesId = ?", (notes, notes_id))
        return {"success": True, "message": "Note updated successfully!"}
    except Exception as e:
        return {"success": False, "message": f"Database error: {str(e)}"}

def delete_note(notes_id):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT notesId FROM users_notes WHERE notesId = ?", (notes_id,))
            data = cursor.fetchone()
            if data is None:
                return {"success": False, "message": f"No note found with NoteId #{notes_id}"}
            cursor.execute("DELETE FROM users_notes WHERE notesId = ?", (notes_id,))
        return {"success": True, "message": "Note deleted successfully!"}
    except Exception as e:
        return {"success": False, "message": f"Database error: {str(e)}"}

def see_all_notes(user_name):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT userId FROM users WHERE userName = ?", (user_name,))
            user = cursor.fetchone()
            if user is None:
                return {"success": False, "message": f"Username '{user_name}' does not exist."}
            user_id = user["userId"]
            cursor.execute(
                "SELECT notesId, notes, timestamp FROM users_notes WHERE userId = ? ORDER BY notesId DESC",
                (user_id,)
            )
            rows = cursor.fetchall()
            if not rows:
                return {"success": False, "message": f"No notes found for username '{user_name}'."}
            notes_list = [
                {"notesId": row["notesId"], "notes": row["notes"], "timestamp": row["timestamp"]}
                for row in rows
            ]
            return {"success": True, "notes": notes_list, "userName": user_name}
    except Exception as e:
        return {"success": False, "message": f"Database error: {str(e)}"}

def delete_all_notes(user_id):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT notesId FROM users_notes WHERE userId = ?", (user_id,))
            data = cursor.fetchall()
            if not data:
                return {"success": False, "message": f"No notes found for UserId {user_id}."}
            cursor.execute("DELETE FROM users_notes WHERE userId = ?", (user_id,))
        return {"success": True, "message": "All notes deleted successfully!"}
    except Exception as e:
        return {"success": False, "message": f"Database error: {str(e)}"}

# Initialize on import
init_db()